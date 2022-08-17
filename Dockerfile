# Copyright 2022 Google LLC
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

FROM python:3.8-slim-buster

ENV APP_HOME /app
ENV PORT 8080
ENV PYTHONUNBUFFERED 1

WORKDIR $APP_HOME
COPY requirements.txt .

RUN pip install --upgrade pip -r requirements.txt

COPY . .
CMD PRODUCTION_MODE="production" python3 manage.py runserver 0.0.0.0:8080
