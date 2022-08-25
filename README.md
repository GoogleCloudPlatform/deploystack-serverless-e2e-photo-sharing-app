# Build an serverless end-to-end photo sharing application with Google Cloud

This repo will help you create an end-to-end social media web app with Google Cloud and Terraform
![architecture](architecture.png)

Components created: 
* Cloud Run - which will run the app as the main server
* Cloud SQL - To store relational database such as user info, posts
* Cloud Storage - To store non-relational database such as post media 
* Cloud Load Balancer - To server traffic with multiple regions 
* Cloud DNS - To map custom domain
* Cloud Build - To automatically deploy your app from gcloud
* Secret Manager - To improve the security of the app
* Cloud VPC - To connect Cloud SQL with Cloud Run via Private improve
* Cloud DNS - to store static cache for faster connections 
* Translation API - to translate the post caption if it is in another language

What you can do with this app: 
* Create post with media and caption
* Search users
* View newsfeed
* Follow other users
* Change profile picture
* Translate the post caption to English

## Install
You can install this application using the `Open in Google Cloud Shell` button 
below. 

<a href="https://ssh.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https://github.com/GoogleCloudPlatform/deploystack-serverless-e2e-photo-sharing-app&shellonly=true&cloudshell_image=gcr.io/ds-artifacts-cloudshell/deploystack_custom_image" target="_new">
    <img alt="Open in Cloud Shell" src="https://gstatic.com/cloudssh/images/open-btn.svg">
</a>

Clicking this link will take you right to the DeployStack app, running in your 
Cloud Shell environment. It will walk you through setting up your architecture.  

## Cleanup 
To remove all billing components from the project
1. Remove componets with terraform apply -auto-approve -var=project=${PROJECT}
2. Typing `deploystack uninstall`

## How to run 
1. Create project with billing enabled, and configure gcloud for that project

   ```
   export PROJECT_ID=foobar
   gcloud config set project $PROJECT_ID
   ```

2. Configure default credentials (allows Terraform to apply changes):

   ```
   gcloud auth application-default login
   ```

3. Enable base services:

   ```
   gcloud services enable \
     cloudbuild.googleapis.com \
     run.googleapis.com \
     vpcaccess.googleapis.com
   ```

4. Build base image

   ```
   gcloud builds submit
   ```

5. Run ```./test```

   Check the output url from Cloud Run

## Migrate your models: 
* Go to Cloud SQL to get your connection name. It should be in the format: {PROJECT_ID}:{SQL_INSTANCE_REGION}:{SQL_INSTANCE_NAME}. 
* Run ```PRODUCTION_MODE="local" python3 manage.py runserver --insecure 0.0.0.0:8080``` to test if the app can be run locally and connected to Cloud SQL. 

* In another terminal, run ```./cloud_sql_proxy -instances={CONNECTION_NAME}=tcp:0.0.0.0:8002```
* On your app's terminal, run ```PRODUCTION_MODE="local" python3 manage.py migrate```

* Run step 4 and step 5 in *How to run* again to apply new changes on server.

Have issues or questions, visit [Issues](https://github.com/GoogleCloudPlatform/deploystack-serverless-e2e-photo-sharing-app/issues).

This is not an official Google product.
