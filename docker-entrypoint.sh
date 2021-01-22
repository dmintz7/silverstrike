#!/bin/bash

# Apply database migrations
echo "Apply database migrations"
python3 /app/manage.py migrate

echo "Initializing Email Configuration File"
sed -i 's/default_url/'$EMAIL_URL'/g' '/app/download.fetchmailrc'
sed -i 's/default_user/'$EMAIL_USER'/g' '/app/download.fetchmailrc'
sed -i 's/default_pass/'$EMAIL_PASS'/g' '/app/download.fetchmailrc'
sed -i 's/default_label/'$EMAIL_LABEL'/g' '/app/download.fetchmailrc'

echo "Create admin user if no user exists"
python3 /app/initialize.py

#Start Server
uwsgi --ini /app/silverstrike.ini
