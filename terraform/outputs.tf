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

output "url" {
  value = "http://${module.lb-http.external_ip}"
  description = "The URL of the load balancer with the external IP address. Use this to set up custom domain mapping."
}

output "SUPERUSER_PASSWORD" {
  value     = google_secret_manager_secret_version.SUPERUSER_PASSWORD.secret_data
  sensitive = true
  description = "superper user password for admin access. Save it to set up superuser account."
}
