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

from datetime import datetime, date
import hashlib
import io
from itertools import chain
import os
import random
import re
import tempfile
import uuid

from django.conf import settings as django_settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, auth
from django.core.exceptions import ValidationError
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from google.cloud import secretmanager, storage, translate_v2 as translate
from PIL import Image, UnidentifiedImageError

from .models import FollowersCount, LikePost, Post, PostGCP, Profile, ProfileGCP

secret_client = secretmanager.SecretManagerServiceClient()
PROJECT_ID = os.environ.get('PROJECT_ID')


def get_secret(secret_name, project_id):
    name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
    response = secret_client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")


GS_BUCKET_NAME = str(get_secret("GS_BUCKET_NAME", PROJECT_ID)) + "-bucket"
storage_client = storage.Client()
translate_client = translate.Client()
bucket = storage_client.bucket(GS_BUCKET_NAME)

MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_IMAGE_FORMATS = {
    "PNG": (".png", "image/png"),
    "JPEG": (".jpg", "image/jpeg"),
    "GIF": (".gif", "image/gif"),
    "WEBP": (".webp", "image/webp"),
}
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
SAFE_GCS_BLOB_RE = re.compile(
    r"^[0-9a-f]{64}/(profile/profile\.(png|jpg|jpeg|gif|webp)|posts/[A-Za-z0-9_.: -]+)$"
)


def _sniff_magic_mime(header):
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate_uploaded_image(uploaded_file):
    """Validates size, extension, content-type, magic bytes, and image structure."""
    if uploaded_file is None:
        raise ValidationError("No image file provided.")

    size = getattr(uploaded_file, "size", None)
    if size is not None and (size <= 0 or size > MAX_UPLOAD_SIZE_BYTES):
        raise ValidationError("Invalid image file size (maximum 10 MB).")

    raw_name = getattr(uploaded_file, "name", "") or ""
    _, ext = os.path.splitext(os.path.basename(raw_name))
    ext = ext.lower()
    if ext and ext not in ALLOWED_EXTENSIONS:
        raise ValidationError("Unsupported file extension.")

    declared_type = getattr(uploaded_file, "content_type", None)
    if declared_type and declared_type.lower() not in ALLOWED_CONTENT_TYPES:
        raise ValidationError("Unsupported file content type.")

    uploaded_file.seek(0)
    data = uploaded_file.read(MAX_UPLOAD_SIZE_BYTES + 1)
    uploaded_file.seek(0)

    if not data or len(data) > MAX_UPLOAD_SIZE_BYTES:
        raise ValidationError("Invalid image payload size (maximum 10 MB).")

    magic_mime = _sniff_magic_mime(data[:16])
    if magic_mime is None:
        raise ValidationError("Uploaded file does not have valid image magic bytes.")

    try:
        with Image.open(io.BytesIO(data)) as img:
            fmt = (img.format or "").upper()
            img.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise ValidationError("Uploaded file is not a valid image.") from exc

    if fmt not in ALLOWED_IMAGE_FORMATS:
        raise ValidationError("Unsupported image format.")

    canonical_ext, canonical_mime = ALLOWED_IMAGE_FORMATS[fmt]
    if canonical_mime != magic_mime:
        raise ValidationError("Image header does not match decoded format.")

    return canonical_ext, canonical_mime


def hash_function(text):
    """Hashes a string using SHA256."""
    return hashlib.sha256(text.encode()).hexdigest()


def gcs_media_url(blob_name):
    return f"/gcs-media/{blob_name}"


@login_required(login_url='signin')
def serve_gcs_media(request, blob_path):
    """Streams validated private user media from GCS to authenticated users."""
    if ".." in blob_path or not SAFE_GCS_BLOB_RE.match(blob_path):
        raise Http404("Media not found")

    blob = bucket.blob(blob_path)
    if not blob.exists():
        raise Http404("Media not found")

    data = blob.download_as_bytes()
    mime = _sniff_magic_mime(data[:16])
    if mime not in ALLOWED_CONTENT_TYPES:
        return HttpResponseForbidden("Invalid media content")

    response = HttpResponse(data, content_type=mime)
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Security-Policy"] = "default-src 'none'; sandbox"
    return response


@login_required(login_url='signin')
@require_POST
def translate(request):
    """Translates the authenticated owner's post caption to English."""
    post_id = request.POST.get('post_id')
    if not post_id:
        return HttpResponseBadRequest("Missing post_id")

    post = get_object_or_404(PostGCP, id=post_id)
    if post.user != request.user.username:
        return HttpResponseForbidden("You can only translate your own posts.")

    result = translate_client.translate(
        post.caption,
        target_language="en",
        format_="text",
    )

    post.caption = result["translatedText"]
    post.save()
    return redirect('/')


def upload_blob_from_memory(bucket_name, contents, destination_blob_name_image, content_type=None):
    """Uploads a local file path to the private GCS bucket."""
    blob = bucket.blob(destination_blob_name_image)
    if content_type:
        blob.upload_from_filename(contents, content_type=content_type)
    else:
        blob.upload_from_filename(contents)


def get_current_time():
    now = datetime.now()
    today = date.today()
    current_time = str(today) + " " + now.strftime("%H:%M:%S")
    return str(current_time)


def list_blobs_posts(prefix):
    blobs = storage_client.list_blobs(GS_BUCKET_NAME, prefix=prefix, delimiter=None)
    blob_list = []
    for blob in blobs:
        blob_list.append(gcs_media_url(blob.name))
    return blob_list


def update_metadata(username, bio=None, location=None):
    hash_userid = hash_function(username)
    blob = bucket.get_blob(str(hash_userid) + "/profile/profile.png")
    if blob is None:
        return

    metadata = {'userid': hash_userid, "username": username}
    if bio is not None:
        metadata['bio'] = bio
    if location is not None:
        metadata['location'] = location

    blob.metadata = metadata
    blob.patch()


def update_metadata_post(username, caption, post_object_key):
    hash_userid = hash_function(username)
    blob = bucket.get_blob(hash_userid + "/posts/" + post_object_key)
    if blob is None:
        return

    metadata = {
        "post_id": hash_function(post_object_key),
        "time_posted": get_current_time(),
        "caption": str(caption),
    }
    blob.metadata = metadata
    blob.patch()


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

    all_users = User.objects.all()
    user_following_all = []

    for user in user_following:
        user_list = User.objects.get(username=user.user)
        user_following_all.append(user_list)

    new_suggestions_list = [x for x in list(all_users) if (x not in list(user_following_all))]
    current_user = User.objects.filter(username=request.user.username)
    final_suggestions_list = [x for x in list(new_suggestions_list) if (x not in list(current_user))]
    random.shuffle(final_suggestions_list)

    username_profile = []
    username_profile_list = []

    for users in final_suggestions_list:
        username_profile.append(users.id)

    for ids in username_profile:
        profile_lists = Profile.objects.filter(id_user=ids)
        username_profile_list.append(profile_lists)

    suggestions_username_profile_list = list(chain(*username_profile_list))

    return render(
        request,
        'index.html',
        {
            'user_profile': user_profile,
            'posts': feed_list,
            'suggestions_username_profile_list': suggestions_username_profile_list[:4],
        },
    )


@login_required(login_url='signin')
def upload(request):
    if request.method == 'POST':
        user = request.user.username
        image = request.FILES.get('image_upload')
        try:
            ext, content_type = validate_uploaded_image(image)
        except ValidationError as exc:
            return HttpResponseBadRequest(exc.message)

        caption = request.POST.get('caption', '')
        hash_userid = str(hash_function(user))

        # Override client-supplied filename with a server-generated UUID before saving.
        safe_filename = f"{uuid.uuid4().hex}{ext}"
        image.name = safe_filename

        new_local_post = Post.objects.create(user=user, image=image, caption=caption)
        local_path = new_local_post.image.path
        media_root_real = os.path.realpath(django_settings.MEDIA_ROOT)
        local_path_real = os.path.realpath(local_path)
        if os.path.commonpath([media_root_real, local_path_real]) != media_root_real:
            raise ValidationError("Invalid storage path.")

        post_object_key = safe_filename
        gcs_blob_name = f"{hash_userid}/posts/{post_object_key}"
        try:
            upload_blob_from_memory(
                GS_BUCKET_NAME,
                local_path_real,
                gcs_blob_name,
                content_type=content_type,
            )
            if caption is not None:
                update_metadata_post(user, caption, post_object_key)

            PostGCP.objects.create(
                user=user,
                image=gcs_media_url(gcs_blob_name),
                caption=caption,
            )
        finally:
            if os.path.exists(local_path_real):
                os.remove(local_path_real)

        return redirect('/')
    return redirect('/')


@login_required(login_url='signin')
def search(request):
    user_object = User.objects.get(username=request.user.username)
    user_profile = ProfileGCP.objects.get(user=user_object)
    username_profile_list = []
    username = ""

    if request.method == 'POST':
        username = request.POST.get('username', '')
        username_object = User.objects.filter(username__icontains=username)

        username_profile = []
        for users in username_object:
            username_profile.append(users.id)

        for ids in username_profile:
            profile_lists = ProfileGCP.objects.filter(id_user=ids)
            username_profile_list.append(profile_lists)

        username_profile_list = list(chain(*username_profile_list))
    return render(
        request,
        'search.html',
        {
            'user_profile': user_profile,
            'username_profile_list': username_profile_list,
            'username': username,
        },
    )


@login_required(login_url='signin')
@require_POST
def like_post(request):
    username = request.user.username
    post_id = request.POST.get('post_id')
    if not post_id:
        return HttpResponseBadRequest("Missing post_id")

    post = get_object_or_404(PostGCP, id=post_id)
    like_filter = LikePost.objects.filter(post_id=str(post.id), username=username).first()

    if like_filter is None:
        LikePost.objects.create(post_id=str(post.id), username=username)
        post.no_of_likes = post.no_of_likes + 1
        post.save()
    else:
        like_filter.delete()
        post.no_of_likes = max(0, post.no_of_likes - 1)
        post.save()
    return redirect('/')


@login_required(login_url='signin')
@require_POST
def delete(request):
    return redirect('/')


@login_required(login_url='signin')
def profile_screen(request, username):
    user_object = get_object_or_404(User, username=username)
    user_profile = get_object_or_404(ProfileGCP, user=user_object)
    user_posts = PostGCP.objects.filter(user=username)
    user_post_length = len(user_posts)

    follower = request.user.username
    if FollowersCount.objects.filter(follower=follower, user=username).first():
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
    user_object = get_object_or_404(User, username=pk)
    user_profile = get_object_or_404(ProfileGCP, user=user_object)

    user_posts = PostGCP.objects.filter(user=pk)
    user_post_length = len(user_posts)

    follower = request.user.username
    if FollowersCount.objects.filter(follower=follower, user=pk).first():
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
        'user_posts_gcp': user_posts_gcp,
    }
    return render(request, 'profile.html', context)


@login_required(login_url='signin')
@require_POST
def follow(request):
    follower = request.user.username
    target_username = request.POST.get('user', '').strip()
    if not target_username:
        return HttpResponseBadRequest("Missing target user")

    target_user = get_object_or_404(User, username=target_username)
    if target_user.username == follower:
        return redirect('/profile/' + target_user.username)

    existing = FollowersCount.objects.filter(follower=follower, user=target_user.username)
    if existing.exists():
        existing.delete()
    else:
        FollowersCount.objects.create(follower=follower, user=target_user.username)

    return redirect('/profile/' + target_user.username)


@login_required(login_url='signin')
def settings(request):
    user_profile = ProfileGCP.objects.get(user=request.user)

    if request.method == 'POST':
        bio = request.POST.get('bio', '')
        location = request.POST.get('location', '')
        username = user_profile.user.username
        hash_userid = hash_function(username)
        uploaded_image = request.FILES.get('image')

        if uploaded_image is None:
            user_profile.bio = bio
            user_profile.location = location
            update_metadata(username, bio, location)
            user_profile.save()
        else:
            try:
                ext, content_type = validate_uploaded_image(uploaded_image)
            except ValidationError as exc:
                return HttpResponseBadRequest(exc.message)

            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
                    for chunk in uploaded_image.chunks():
                        tmp_file.write(chunk)
                    tmp_path = tmp_file.name

                gcs_profile_blob = f"{hash_userid}/profile/profile.png"
                upload_blob_from_memory(
                    GS_BUCKET_NAME,
                    tmp_path,
                    gcs_profile_blob,
                    content_type=content_type,
                )
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)

            update_metadata(username, bio, location)
            user_profile.profileimg = gcs_media_url(gcs_profile_blob)
            user_profile.bio = bio
            user_profile.location = location
            user_profile.save()

    return render(request, 'setting.html', {'user_profile': user_profile})


def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username', '')
        email = request.POST.get('email', '')
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')

        if not username or not password:
            messages.info(request, 'Username and password are required')
            return redirect('signup')

        if password == password2:
            if User.objects.filter(email=email).exists():
                messages.info(request, 'Email Taken')
                return redirect('signup')
            if User.objects.filter(username=username).exists():
                messages.info(request, 'Username Taken')
                return redirect('signup')

            user = User.objects.create_user(username=username, email=email, password=password)
            user.save()

            hash_userid = hash_function(username)
            gcs_profile_blob = f"{hash_userid}/profile/profile.png"
            placeholder_path = os.path.join(django_settings.MEDIA_ROOT, "blank-profile-picture.png")
            upload_blob_from_memory(
                GS_BUCKET_NAME,
                placeholder_path,
                gcs_profile_blob,
                content_type="image/png",
            )

            blob = bucket.get_blob(gcs_profile_blob)
            if blob is not None:
                blob.metadata = {'userid': hash_userid, 'username': username}
                blob.patch()

            user_login = auth.authenticate(username=username, password=password)
            auth.login(request, user_login)

            new_profile = ProfileGCP.objects.create(
                user=user,
                id_user=user.id,
                profileimg=gcs_media_url(gcs_profile_blob),
            )
            new_profile.save()

            return render(request, 'setting.html', {"user_id": hash_userid, "user_profile": new_profile})

        messages.info(request, 'Password Not Matching')
        return redirect('signup')

    return render(request, 'signup.html')


def signin(request):
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')

        user = auth.authenticate(username=username, password=password)
        if user is not None:
            auth.login(request, user)
            return redirect('/')

        messages.info(request, 'Credentials Invalid')
        return redirect('signin')

    return render(request, 'signin.html')


@login_required(login_url='signin')
@require_POST
def logout(request):
    auth.logout(request)
    return redirect('signin')
