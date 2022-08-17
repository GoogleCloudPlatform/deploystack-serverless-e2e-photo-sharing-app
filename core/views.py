
# Copyright 2022 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.shortcuts import render, redirect
from django.contrib.auth.models import User, auth
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import PostGCP, Profile, Post, LikePost, FollowersCount, ProfileGCP
from itertools import chain
import random
import os
import hashlib
from datetime import datetime, date
from google.cloud import storage,secretmanager, translate_v2 as translate

secret_client = secretmanager.SecretManagerServiceClient()
PROJECT_ID = os.environ.get('PROJECT_ID')

def get_secret(secret_name, project_id):
    name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
    response = secret_client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

GS_BUCKET_NAME = str(get_secret("BUCKET_NAME", PROJECT_ID)) + "-bucket" 
storage_client = storage.Client()
translate_client = translate.Client()
bucket = storage_client.bucket(GS_BUCKET_NAME)

def hash_function(text): 
    """Hashes a string using SHA256."""
    return hashlib.sha256(text.encode()).hexdigest()

def translate(request):
    """Detects the text's language."""
    post_id = request.GET.get('post_id')
    post = PostGCP.objects.get(id=post_id)
    post_caption = post.caption
    
    result = translate_client.translate(post_caption, target_language="en")

    print(u"Translation: {}".format(result["translatedText"]))
    post.caption = result["translatedText"]
    post.save()
    return redirect('/')


def upload_blob_from_memory(bucket_name, contents, destination_blob_name_image):
    """Uploads a file to the bucket."""
    storage_client = storage.Client()
    blob = bucket.blob(destination_blob_name_image)
    blob.upload_from_filename(contents)

    print(
        f"{destination_blob_name_image} with contents {contents} uploaded to {bucket_name}."
    )


def get_current_time(): 
    now = datetime.now()
    today = date.today()
    current_time = str(today) + " "+ now.strftime("%H:%M:%S") 
    return str(current_time)

def list_blobs_posts(prefix):
    blobs = storage_client.list_blobs(GS_BUCKET_NAME, prefix=prefix, delimiter=None)

    print("Blobs:")
    blob_list = []
    for blob in blobs:
        blob_list.append("https://storage.cloud.google.com/" + GS_BUCKET_NAME + "/" + blob.name)

    return blob_list

def update_metadata(username, bio=None, location=None): 
    hash_userid = hash_function(username)
    blob = bucket.get_blob(str(hash_userid) + "/profile/profile.png")

    if bio is not None:
        metadata = {'userid': hash_userid, "username": username, 'bio': bio}
    
    if location is not None: 
        metadata = {'userid': hash_userid, "username": username, 'bio': bio, "location": location}
    blob.metadata = metadata
    blob.patch()

    print("Metadata updated")


def update_metadata_post(username, caption, current_time_str): 
    hash_userid = hash_function(username)
    blob = bucket.get_blob(hash_userid + "/posts/" + current_time_str)

    metadata = {"post_id": hash_function(current_time_str), "time_posted": current_time_str, "caption": caption}

    blob.metadata = metadata
    blob.patch()

    print("Post metadata updated")

@login_required(login_url='signin')
def index(request):
    user_object = User.objects.get(username=request.user.username)
    user_profile = ProfileGCP.objects.get(user=user_object)

    user_following_list = []
    feed = []

    user_following = FollowersCount.objects.filter(follower=request.user.username)

    for users in user_following:
        user_following_list.append(users.user)

    for usernames in user_following_list:
        feed_lists = PostGCP.objects.filter(user=usernames)
        feed.append(feed_lists)
    feed_list = list(chain(*feed))

    # user suggestion starts
    all_users = User.objects.all()
    user_following_all = []

    for user in user_following:
        user_list = User.objects.get(username=user.user)
        user_following_all.append(user_list)
    
    new_suggestions_list = [x for x in list(all_users) if (x not in list(user_following_all))]
    current_user = User.objects.filter(username=request.user.username)
    final_suggestions_list = [x for x in list(new_suggestions_list) if ( x not in list(current_user))]
    random.shuffle(final_suggestions_list)

    username_profile = []
    username_profile_list = []

    for users in final_suggestions_list:
        username_profile.append(users.id)

    for ids in username_profile:
        profile_lists = Profile.objects.filter(id_user=ids)
        username_profile_list.append(profile_lists)

    suggestions_username_profile_list = list(chain(*username_profile_list))

    return render(request, 'index.html', {'user_profile': user_profile, 'posts':feed_list, 'suggestions_username_profile_list': suggestions_username_profile_list[:4]})

@login_required(login_url='signin')
def upload(request):
    now = datetime.now()
    today = date.today().strftime("%m-%d-%y")
    dt_string = today + "/" + now.strftime("%H:%M:%S")

    if request.method == 'POST':
        user = request.user.username
        image = request.FILES.get('image_upload')
        image_str = str(image)
        caption = request.POST.get('caption', False)

        hash_userid = str(hash_function(user))
        time = get_current_time()
        new_post = Post.objects.create(user=user, image=image, caption=caption)
        new_post.save()

        upload_blob_from_memory(GS_BUCKET_NAME, "media/post_images/" + image_str,  hash_userid + "/posts/" + time)
        
        if caption is not None: 
            update_metadata_post(user, caption, time)

        blob = bucket.get_blob(hash_userid + "/posts/" + time)
        
        new_post = PostGCP.objects.create(user=user, image="https://storage.cloud.google.com/" + GS_BUCKET_NAME + "/" + blob.name, caption=caption)
        new_post.save()

        print(caption)
        os.remove("media/post_images/" + image_str) 

        return redirect('/')
    else:
        return redirect('/')

@login_required(login_url='signin')
def search(request):
    user_object = User.objects.get(username=request.user.username)
    user_profile = ProfileGCP.objects.get(user=user_object)

    if request.method == 'POST':
        username = request.POST['username']
        username_object = User.objects.filter(username__icontains=username)

        username_profile = []
        username_profile_list = []

        for users in username_object:
            username_profile.append(users.id)

        for ids in username_profile:
            profile_lists = ProfileGCP.objects.filter(id_user=ids)
            username_profile_list.append(profile_lists)
        
        username_profile_list = list(chain(*username_profile_list))
    return render(request, 'search.html', {'user_profile': user_profile, 'username_profile_list': username_profile_list})

@login_required(login_url='signin')
def like_post(request):
    username = request.user.username
    post_id = request.GET.get('post_id')

    post = PostGCP.objects.get(id=post_id)

    like_filter = LikePost.objects.filter(post_id=post_id, username=username).first()

    if like_filter == None:
        new_like = LikePost.objects.create(post_id=post_id, username=username)
        new_like.save()
        post.no_of_likes = post.no_of_likes+1
        post.save()
        return redirect('/')
    else:
        like_filter.delete()
        post.no_of_likes = post.no_of_likes-1
        post.save()
        return redirect('/')

@login_required(login_url='signin')
def delete(request): 
    return redirect('/')

@login_required(login_url='signin')
def profile_screen(request, username):
    user_object = User.objects.get(username=username)
    user_profile = ProfileGCP.objects.get(user=user_object)
    user_posts = PostGCP.objects.filter(user=username)
    user_post_length = len(user_posts)

    follower = request.user.username
    user = username

    if FollowersCount.objects.filter(follower=follower, user=user).first():
        button_text = 'Unfollow'
    else:
        button_text = 'Follow'

    user_followers = len(FollowersCount.objects.filter(user=username))
    user_following = len(FollowersCount.objects.filter(follower=username))

    context = {
        'user_object': user_object,
        'user_profile': user_profile,
        'user_posts': user_posts,
        'user_post_length': user_post_length,
        'button_text': button_text,
        'user_followers': user_followers,
        'user_following': user_following,
    }

    return render(request, 'profile.html', context)

@login_required(login_url='signin')
def profile(request, pk):
    user_object = User.objects.get(username=pk)
    user_profile = ProfileGCP.objects.get(user=user_object)

    posts = list_blobs_posts(hash_function(pk) + "/posts/")

    user_posts = PostGCP.objects.filter(user=pk)
    user_post_length = len(user_posts)

    follower = request.user.username
    user = pk

    if FollowersCount.objects.filter(follower=follower, user=user).first():
        button_text = 'Unfollow'
    else:
        button_text = 'Follow'

    user_followers = len(FollowersCount.objects.filter(user=pk))
    user_following = len(FollowersCount.objects.filter(follower=pk))

    user_posts_gcp = list_blobs_posts(hash_function(pk) + "/posts/")
    
    context = {
        'user_object': user_object,
        'user_profile': user_profile,
        'user_posts': user_posts,
        'user_post_length': user_post_length,
        'button_text': button_text,
        'user_followers': user_followers,
        'user_following': user_following,
        "user_posts_gcp": user_posts_gcp,
    }

    return render(request, 'profile.html', context)

@login_required(login_url='signin')
def follow(request):
    if request.method == 'POST':
        follower = request.POST['follower']
        user = request.POST['user']

        if FollowersCount.objects.filter(follower=follower, user=user).first():
            delete_follower = FollowersCount.objects.get(follower=follower, user=user)
            delete_follower.delete()
            return redirect('/profile/'+user)
        else:
            new_follower = FollowersCount.objects.create(follower=follower, user=user)
            new_follower.save()
            return redirect('/profile/'+user)
    else:
        return redirect('/')


@login_required(login_url='signin')
def settings(request):
    user_profile = ProfileGCP.objects.get(user=request.user)

    if request.method == 'POST':
        if request.FILES.get('image') == None:
            image = user_profile.profileimg
            bio = request.POST['bio']
            location = request.POST['location']
            username = user_profile.user.username
            hash_userid = hash_function(username) 

            user_profile.profileimg = image
            user_profile.bio = bio
            user_profile.location = location

            update_metadata(username, bio, location)

            user_profile.save()

        if request.FILES.get('image') != None:
            image = request.FILES.get('image')
            bio = request.POST['bio']
            location = request.POST['location']
            username = user_profile.user.username
            hash_userid = hash_function(username) 
           
            with open("media/blank-profile-picture.png", 'wb') as f:
                f.write(image.read())

            upload_blob_from_memory(GS_BUCKET_NAME, "media/blank-profile-picture.png", hash_userid + "/profile/profile.png")
            update_metadata(username, bio, location)

            user_profile.profileimg = "https://storage.cloud.google.com/" + GS_BUCKET_NAME + "/" + hash_userid + "/profile/profile.png"
            user_profile.bio = bio
            user_profile.location = location
            user_profile.save()

            # os.remove("media/profile_images/" + str(image))
    return render(request, 'setting.html', {'user_profile': user_profile})


def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username', False)
        email = request.POST.get('email', False)
        password = request.POST.get('password', False)
        password2 = request.POST.get('password2', False)

        if password == password2:
            if User.objects.filter(email=email).exists():
                messages.info(request, 'Email Taken')
                return redirect('signup')
            elif User.objects.filter(username=username).exists():
                messages.info(request, 'Username Taken')
                return redirect('signup')
            else:
                user = User.objects.create_user(username=username, email=email, password=password)
                user.save()

                hash_userid = hash_function(username)
                upload_blob_from_memory(GS_BUCKET_NAME, "media/blank-profile-picture.png", str(hash_userid) + "/profile/profile.png")
                
                blob = bucket.get_blob(str(hash_userid) + "/profile/profile.png")
                metadata = {'userid': hash_userid, username: username}
                blob.metadata = metadata
                blob.patch()
                
                #log user in and redirect to settings page
                user_login = auth.authenticate(username=username, password=password)
                auth.login(request, user_login)

                #create a Profile object for the new user
                image_file_url = "https://storage.cloud.google.com/" + GS_BUCKET_NAME + "/" + str(hash_userid) + "/profile/profile.png"
                user_model = User.objects.get(username=username)
                new_profile = ProfileGCP.objects.create(user=user_model, id_user=user_model.id, profileimg=image_file_url)
                new_profile.save()

                return render(request, 'setting.html', {"user_id": hash_userid})
        else:
            messages.info(request, 'Password Not Matching')
            return redirect('signup')
        
    else:
        return render(request, 'signup.html')

def signin(request):
    if request.method == 'POST':
        username = request.POST.get('username', False)
        password = request.POST.get('password', False)

        user = auth.authenticate(username=username, password=password)
        
        if user is not None:
            auth.login(request, user)
            return redirect('/')
        else:
            messages.info(request, 'Credentials Invalid')
            return redirect('signin')

    else:
        return render(request, 'signin.html')

@login_required(login_url='signin')
def logout(request):
    auth.logout(request)
    return redirect('signin')


