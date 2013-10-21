#!/usr/bin/python
'''
Created on 6 Jun 2012

@author: Jeremy Blythe

Motion Uploader - uploads videos to Google Drive

Read the blog entry at http://jeremyblythe.blogspot.com for more information
'''

import smtplib
from datetime import datetime

import os.path
import sys
import httplib2

import ConfigParser

from apiclient.discovery import build
from apiclient.http import MediaFileUpload
from oauth2client.client import AccessTokenCredentials

from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email import Encoders

class MotionUploader:
    def __init__(self, config_file_path):
        # Load config
        config = ConfigParser.ConfigParser()
        config.read(config_file_path)
        
        # GMail account credentials
        self.username = config.get('gmail', 'user')
        self.password = config.get('gmail', 'password')
        self.from_name = config.get('gmail', 'name')
        self.sender = config.get('gmail', 'sender')
        
        # Recipient email address (could be same as from_addr)
        self.recipient = config.get('gmail', 'recipient')        
        
        # Subject line for email
        self.subject = config.get('gmail', 'subject')
        
        # First line of email message
        self.message = config.get('gmail', 'message')
                
        # Folder (or collection) in Docs where you want the videos to go
        self.folder = config.get('docs', 'folder')
        
        # Options
        self.delete_after_upload = config.getboolean('options', 'delete-after-upload')
        self.send_email = config.getboolean('options', 'send-email')

        # Auth token for Google Drive
        self.auth_token = config.get('drive', 'auth_token')
    
    def _send_email(self,msg,video_link):
        '''Send an email using the GMail account.'''
        senddate=datetime.strftime(datetime.now(), '%Y-%m-%d')

        m = MIMEMultipart()
        m['From'] = self.sender
        m['To'] = self.recipient
        m['Date'] = senddate
        
        m.attach( MIMEText(msg) )

        dir, fileext = os.path.split(video_link)
        file, ext = os.path.splitext(fileext)
        cam_name = os.path.basename(dir)
        m['Subject'] = self.subject + ' (' + cam_name + ')'

        # Attach a jpeg from the capture
        image = os.path.join(dir, 'motion.jpg')
        part = MIMEBase('application', "octet-stream")
        part.set_payload(open(image, "rb").read())
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(image))
        m.attach(part)

        server = smtplib.SMTP('smtp.gmail.com:587')
        server.starttls()
        server.login(self.username, self.password)
        server.sendmail(self.sender, self.recipient, m.as_string())
        server.quit()

    def _get_drive_service(self):
        credentials = AccessTokenCredentials.new_from_json(self.auth_token)

        # Create an httplib2.Http object and authorize it with our credentials
        http = httplib2.Http()
        http = credentials.authorize(http)

        # Refresh the credentials as necessary
        if credentials.access_token_expired:
            credentials.refresh(http)

        drive_service = build('drive', 'v2', http=http)
        return drive_service

    def upload_video(self, video_file_path):
        drive_service = self._get_drive_service()

        # Insert a file
        dir, fileext = os.path.split(video_file_path)
        media_body = MediaFileUpload(video_file_path, mimetype='video/avi', resumable=True)
        body = {
          'title': fileext,
          'parents': [ { 'id': '0B0GWyudyaoJxQXpNN3h2NWp5ZjA' } ],
          'description': fileext,
          'mimeType': 'video/avi'
        }
        
        file = drive_service.files().insert(body=body, media_body=media_body).execute()

        if self.send_email:
            video_link = file['alternateLink']

            # Send an email with the link if found
            msg = self.message
            if video_link:
                msg += '\n\n' + video_link                
            self._send_email(msg, video_file_path)

        if self.delete_after_upload:
            os.remove(video_file_path)

if __name__ == '__main__':         
    try:
        if len(sys.argv) < 3:
            exit('Motion Uploader - uploads videos to Google Drive\n   by Jeremy Blythe (http://jeremyblythe.blogspot.com)\n\n   Usage: uploader.py {config-file-path} {video-file-path}')
        cfg_path = sys.argv[1]
        vid_path = sys.argv[2]    
        if not os.path.exists(cfg_path):
            exit('Config file does not exist [%s]' % cfg_path)    
        if not os.path.exists(vid_path):
            exit('Video file does not exist [%s]' % vid_path)    
        MotionUploader(cfg_path).upload_video(vid_path)        
    except Exception as e:
        exit('Error: [%s]' % e)
