#!/bin/bash

# Apply database migrations
echo "Apply database migrations"
python3 /app/manage.py migrate

echo "Initializing Email Configuration File"
sed -i 's/default_url/'$EMAIL_URL'/g' '/app/download.fetchmailrc'
sed -i 's/default_user/'$EMAIL_USER'/g' '/app/download.fetchmailrc'
sed -i 's/default_pass/'$EMAIL_PASS'/g' '/app/download.fetchmailrc'
sed -i 's/default_label/'$EMAIL_LABEL'/g' '/app/download.fetchmailrc'

# Create admin user if no user exists
python3 /app/initialize.py

#####################################################
#####################################################
#####################################################
#####################################################
#####################################################
#####################################################

# TEMP FIX FOR EMOJI

version=$(pip3 freeze | grep emoji)
if python3 -c "import emoji" &> /dev/null; then
	echo "Emoji Can Load"
else
	echo "Emoji Errored Loading- Current Version "$version
	if [[ "$version" == *1.2.0* ]]; then
	  pip3 install emoji==0.6.0
	else
	  pip3 install emoji==1.2.0
	fi
fi

#####################################################
#####################################################
#####################################################
#####################################################
#####################################################
#####################################################

# Start Server
echo "Starting Server"
uwsgi --ini /app/silverstrike.ini
