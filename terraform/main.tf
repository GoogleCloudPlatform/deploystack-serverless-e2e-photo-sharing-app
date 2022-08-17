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

# Step 1: Activate Google Cloud
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 3.66"
    }
  }
}

provider "google" {
  project = var.project
  region  = var.region
}

data "google_project" "project" {
  project_id = var.project
}

# Step 2: Activate service APIs
resource "google_project_service" "run" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "sql-component" {
  service            = "sql-component.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "sqladmin" {
  service            = "sqladmin.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "compute" {
  service            = "compute.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "domain" {
  service            = "compute.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloudbuild" {
  service            = "cloudbuild.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "secretmanager" {
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "vpcaccess" {
  service            = "vpcaccess.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "servicenetworking" {
  service            = "servicenetworking.googleapis.com"
  disable_on_destroy = false
}

# Step 3: Create compute networks
# ------------------------------------------------------------------------------
# SEVERLESS VPC CONNECTOR FOR CLOUD SQL
# ------------------------------------------------------------------------------
resource "google_compute_network" "main" {
  provider = google
  name = "social-media-network-${random_id.name.hex}"
}

resource "google_compute_global_address" "private_ip_address" {
  provider = google-beta
  project   = var.project
  name          = local.private_ip_name
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.main.id
  depends_on = [google_project_service.vpcaccess]
}

resource "google_service_networking_connection" "private_vpc_connection" {
  provider = google-beta

  network                 = google_compute_network.main.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
  depends_on = [google_project_service.vpcaccess]
}

resource "google_vpc_access_connector" "connector" {
  for_each = {"us-west1": 8, "us-central1": 9, "us-east1": 10}
  name          = "vpc-con-${each.key}"
  ip_cidr_range = "10.${each.value}.0.0/28"
  region        = each.key
  network       = google_compute_network.main.name
  depends_on = [google_project_service.vpcaccess]
}


# Step 4: Create a custom Service Account
resource "google_service_account" "django" {
  account_id = "django"
}

# Step 5: Create the database
resource "random_string" "random" {
  length           = 4
  special          = false
}

resource "random_password" "database_password" {
  length  = 32
  special = false
}

resource "random_id" "name" {
  byte_length = 2
}

resource "random_id" "db_name_suffix" {
  byte_length = 4
}

resource "google_sql_database_instance" "instance" {
  name             = "sql-database-${random_id.db_name_suffix.hex}"
  database_version = "MYSQL_8_0"
  region           = var.region
  depends_on = [google_vpc_access_connector.connector, google_compute_network.main]
  settings {
    tier = "db-f1-micro"
    ip_configuration {
      ipv4_enabled    = "true"
      private_network = google_compute_network.main.id
    }
  }
  deletion_protection = true
}

resource "google_sql_database" "database" {
  name     = "django"
  instance = google_sql_database_instance.instance.name
}

resource "google_sql_user" "django" {
  name     = "django"
  instance = google_sql_database_instance.instance.name
  password = random_password.database_password.result
}


# Step 6: Create Cloud Storage
resource "google_storage_bucket" "media" {
  name     = "${var.project}-bucket"
  location = "US"
}

resource "google_storage_bucket_iam_binding" "main" {
  bucket = google_storage_bucket.media.name
  role = "roles/storage.objectViewer"
  members = [
    "allUsers",
  ]
}

# Step 7: Prepare the secrets for Django
resource "google_secret_manager_secret_version" "django_settings" {
  secret = google_secret_manager_secret.django_settings.id

  secret_data = templatefile("etc/env.tpl", {
    bucket     = google_storage_bucket.media.name
    secret_key = random_password.django_secret_key.result
    user       = google_sql_user.django
    instance   = google_sql_database_instance.instance
    database   = google_sql_database.database
  })
}

resource "random_password" "django_secret_key" {
  special = false
  length  = 50
}

resource "google_secret_manager_secret" "django_settings" {
  secret_id = "django_settings"

  replication {
    automatic = true
  }
  depends_on = [google_project_service.secretmanager]

}

# Step 8: Expand Service Account permissions
resource "google_secret_manager_secret_iam_binding" "django_settings" {
  secret_id = google_secret_manager_secret.django_settings.id
  role      = "roles/secretmanager.admin"
  members   = [local.cloudbuild_serviceaccount, local.django_serviceaccount]
}

locals {
  cloudbuild_serviceaccount = "serviceAccount:${data.google_project.project.number}@cloudbuild.gserviceaccount.com"
  django_serviceaccount     = "serviceAccount:${google_service_account.django.email}"
  private_network_name = "network-${random_id.name.hex}"
  private_ip_name      = "private-ip-${random_id.name.hex}"
}


# Step 9: Populate secrets
resource "google_secret_manager_secret" "main" {
   for_each = { 
      "DATABASE_PASSWORD": google_sql_user.django.password,
      "DATABASE_USER": google_sql_user.django.name,
      "DATABASE_NAME": google_sql_database.database.name, 
      "DATABASE_HOST_PROD": google_sql_database_instance.instance.private_ip_address,
      "DATABASE_PORT_PROD": 3306, 
      "EXTERNAL_IP": module.lb-http.external_ip,
      "PROJECT_ID": var.project, 
      "GS_BUCKET_NAME":var.project, 
      "WEBSITE_URL_US_CENTRAL1": google_cloud_run_service.service["us-central1"].status[0].url,
      "WEBSITE_URL_US_WEST1": google_cloud_run_service.service["us-west1"].status[0].url,
      "WEBSITE_URL_US_EAST1": google_cloud_run_service.service["us-east1"].status[0].url,
    }
    secret_id = "${each.key}"
    replication {
      automatic = true
    }
    
   depends_on = [google_project_service.secretmanager, google_sql_user.django, google_sql_database.database, google_sql_database_instance.instance]

}

resource "google_secret_manager_secret_version" "main" {
  for_each = { "DATABASE_PASSWORD": google_sql_user.django.password,
    "DATABASE_USER": google_sql_user.django.name,
    "DATABASE_NAME": google_sql_database.database.name, 
    "DATABASE_HOST_PROD": google_sql_database_instance.instance.private_ip_address,
    "DATABASE_PORT_PROD": 3306, 
    "EXTERNAL_IP": module.lb-http.external_ip,
    "PROJECT_ID": var.project, 
    "GS_BUCKET_NAME":var.project, 
    "WEBSITE_URL_US_CENTRAL1": google_cloud_run_service.service["us-central1"].status[0].url,
    "WEBSITE_URL_US_WEST1": google_cloud_run_service.service["us-west1"].status[0].url,
    "WEBSITE_URL_US_EAST1": google_cloud_run_service.service["us-east1"].status[0].url,  }
  secret      = google_secret_manager_secret.main[each.key].id
  secret_data = "${each.value}"
}

resource "google_secret_manager_secret_iam_binding" "main" {
  for_each = { "DATABASE_PASSWORD": google_sql_user.django.password,
    "DATABASE_USER": google_sql_user.django.name,
    "DATABASE_NAME": google_sql_database.database.name, 
    "DATABASE_HOST_PROD": google_sql_database_instance.instance.private_ip_address,
    "DATABASE_PORT_PROD": 3306, 
    "EXTERNAL_IP": module.lb-http.external_ip,
    "PROJECT_ID": var.project, 
    "GS_BUCKET_NAME":var.project, 
    "WEBSITE_URL_US_CENTRAL1": google_cloud_run_service.service["us-central1"].status[0].url,
    "WEBSITE_URL_US_WEST1": google_cloud_run_service.service["us-west1"].status[0].url,
    "WEBSITE_URL_US_EAST1": google_cloud_run_service.service["us-east1"].status[0].url,}
  secret_id = google_secret_manager_secret.main[each.key].id
  role      = "roles/secretmanager.secretAccessor"
  members   = [local.cloudbuild_serviceaccount]
}

# ------------------------------------------------------------------------------
# superuser_password
# ------------------------------------------------------------------------------

resource "random_password" "SUPERUSER_PASSWORD" {
  length  = 32
  special = false
}

resource "google_secret_manager_secret" "SUPERUSER_PASSWORD" {
  secret_id = "SUPERUSER_PASSWORD"
  replication {
    automatic = true
  }
  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret_version" "SUPERUSER_PASSWORD" {
  secret      = google_secret_manager_secret.SUPERUSER_PASSWORD.id
  secret_data = random_password.SUPERUSER_PASSWORD.result
}

resource "google_secret_manager_secret_iam_binding" "SUPERUSER_PASSWORD" {
  secret_id = google_secret_manager_secret.SUPERUSER_PASSWORD.id
  role      = "roles/secretmanager.secretAccessor"
  members   = [local.cloudbuild_serviceaccount]
}


# Step 10: Create Cloud Run service
data "google_cloud_run_locations" "default" { }

resource "google_cloud_run_service" "service" {
  for_each = toset([for location in data.google_cloud_run_locations.default.locations : location if can(regex("us-(?:west|central|east)1", location))])
  name                       = "${var.project}"
  location                   = each.value
  project                    = var.project
  autogenerate_revision_name = true
  depends_on = [google_sql_database_instance.instance]

  template {
    spec {
      service_account_name = google_service_account.django.email
      containers {
        image = "gcr.io/${var.project}/${var.service}:latest"
        env {
          name = "PROJECT_ID"
          value = var.project
        }
      }
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale"      = "100"
        "run.googleapis.com/cloudsql-instances" = google_sql_database_instance.instance.connection_name
        "run.googleapis.com/client-name"        = "terraform"
        "run.googleapis.com/vpc-access-connector" = google_vpc_access_connector.connector[each.key].name
        "run.googleapis.com/vpc-access-egress"    = "all-traffic"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

data "google_iam_policy" "noauth" {
  binding {
    role = "roles/run.invoker"
    members = [
      "allUsers",
    ]
  }
}

resource "google_cloud_run_service_iam_policy" "noauth" {
  for_each = toset([for location in data.google_cloud_run_locations.default.locations : location if can(regex("us-(?:west|central|east)1", location))])
  location = google_cloud_run_service.service[each.key].location
  project  = google_cloud_run_service.service[each.key].project 
  service  = google_cloud_run_service.service[each.key].name

  policy_data = data.google_iam_policy.noauth.policy_data
}


# Step 11: Create Load Balancer to handle traffics from multiple regions 
resource "google_compute_region_network_endpoint_group" "default" {
  for_each = toset([for location in data.google_cloud_run_locations.default.locations : location if can(regex("us-(?:west|central|east)1", location))])
  name                  = "${var.project}--neg--${each.key}"
  network_endpoint_type = "SERVERLESS"
  region                = google_cloud_run_service.service[each.key].location
  cloud_run { 
    service = google_cloud_run_service.service[each.key].name
  }
}

module "lb-http" {
  source            = "GoogleCloudPlatform/lb-http/google//modules/serverless_negs"
  version           = "~> 4.5"

  project = var.project
  name    = var.project

  ssl = false
  https_redirect = true
  managed_ssl_certificate_domains = []
  use_ssl_certificates            = false
  backends = {
    default = {
      description            = null
      enable_cdn             = true
      custom_request_headers = null
  
      log_config = {
        enable      = true
        sample_rate = 1.0
      }

      groups = [
        for neg in google_compute_region_network_endpoint_group.default:
        {
          group = neg.id
        }
      ]

      iap_config = {
        enable               = false
        oauth2_client_id     = null
        oauth2_client_secret = null
      }
      security_policy = null
    }
  }
}


# Step 12: Grant access to the database
resource "google_project_iam_binding" "service_permissions" {
  for_each = toset([
    "run.admin", "cloudsql.client", "editor", "secretmanager.admin"
  ])

  role    = "roles/${each.key}"
  members = [local.cloudbuild_serviceaccount, local.django_serviceaccount]
}

resource "google_service_account_iam_binding" "cloudbuild_sa" {
  service_account_id = google_service_account.django.name
  role               = "roles/iam.serviceAccountUser"

  members = [local.cloudbuild_serviceaccount]
}