# Build an serverless end-to-end photo sharing application with Google Cloud

This deploystack will help you create a scalable end-to-end photo-sharing application with 11 Google Cloud, Terraform, and Django. 

## Architecture

![architecture](architecture.png)

**Components created:** 
* Cloud Run - which will run the app as the main server.
* Cloud SQL - To store relational database such as user info, posts.
* Cloud Storage - To store non-relational database such as post media. 
* Cloud Load Balancer - To server traffic with multiple regions. 
* Cloud DNS - To map custom domain and handle requests from your local machines everytime you go to the url.  
* Cloud Build - apply DevOps CI/CD to automatically deploy your app from gcloud.
* Secret Manager - To improve the security of the app.
* Cloud VPC - To connect Cloud SQL with Cloud Run via private network. 
* Cloud DNS - to store static cache for faster connections.
* Translation API - to translate the post caption if it is in another language.
* Container Registry - to store, manage, and secure your Docker container images.

**What you can do with this app:**
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
**1. Create project with billing enabled, and configure gcloud for that project**

   ```
   export PROJECT_ID=foobar
   gcloud config set project $PROJECT_ID
   ```

**2. Configure default credentials (allows Terraform to apply changes):**

   ```
   gcloud auth application-default login
   ```
   
   To double check, run ```gcloud auth list```
   To set active account, run gcloud config set account `ACCOUNT`

**3. Enable base services:**

   ```
   gcloud services enable \
     cloudbuild.googleapis.com \
     run.googleapis.com \
     vpcaccess.googleapis.com
   ```

**4. Build base image**

   ```
   gcloud builds submit
   ```

**5. Run** ```./test```

   Check the output url from Cloud Run

## Local deployment: 
1. Go to Cloud SQL to get your connection name. It should be in the format: ```{PROJECT_ID}:{SQL_INSTANCE_REGION}:{SQL_INSTANCE_NAME}```
2. In another terminal, run ```./cloud_sql_proxy -instances={CONNECTION_NAME}=tcp:0.0.0.0:8002```
3. Run ```PRODUCTION_MODE="local" python3 manage.py runserver --insecure 0.0.0.0:8080``` to run the app locally and connect to Cloud SQL.

### Django models migration 
1. Follow steps in **local deployment** 
2. On your app's terminal, run**```PRODUCTION_MODE="local" python3 manage.py migrate```
3. Build base image to push new changes to Container Registry 

   ```
   gcloud builds submit
   ```

4. Run ```./test```

   Check the output url from Cloud Run with new changes


---
Have issues or questions, visit [Issues](https://github.com/GoogleCloudPlatform/deploystack-serverless-e2e-photo-sharing-app/issues).

This is not an official Google product.
