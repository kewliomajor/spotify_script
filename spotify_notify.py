import requests
import base64
import json
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from secrets import client_id, client_secret, to_email, from_email, from_email_password

token_url = 'https://accounts.spotify.com/api/token'
new_releases_url = 'https://api.spotify.com/v1/browse/new-releases?country=US&limit=50'


def get_authentication_token(client_id, client_secret):
    encoded_credentials = base64.b64encode((client_id + ':' + client_secret).encode()).decode(encoding='UTF-8')
    resp = requests.post(token_url, data={'grant_type': 'client_credentials'},
                         headers={'Authorization': 'Basic ' + encoded_credentials})
    if resp.status_code != 200:
        raise Exception(token_url + ' {}: {}'.format(resp.status_code, resp.content))
    token_json = json.loads(resp.content.decode(encoding='UTF-8'))
    return token_json['access_token']


def get_album_list_page(url, access_token):
    resp = requests.get(url, headers={'Authorization': 'Bearer ' + access_token})
    if resp.status_code != 200:
        raise Exception(new_releases_url + ' {}: {}'.format(resp.status_code, resp.content))

    return json.loads(resp.content.decode(encoding='UTF-8'))


def email_object_to_string(email_object):
    msg = 'Artist(s): '
    for artist_object in email_object['artists']:
        msg += artist_object['name'] + ' '
    msg += '\nUrl: ' + email_object['external_urls']['spotify'] + '\n'
    msg += 'Album name: ' + email_object['name'] + '\n'
    msg += 'Release date: ' + email_object['release_date'] + '\n'
    msg += 'Tracks: ' + str(email_object['total_tracks']) + '\n\n'
    return msg


access_token = get_authentication_token(client_id, client_secret)
response_content = get_album_list_page(new_releases_url, access_token)
albums = response_content['albums']['items']

while response_content['albums']['next'] is not None and datetime.strptime(response_content['albums']['items'][0]['release_date'], '%Y-%m-%d') > (datetime.today() - timedelta(days=30)):
    response_content = get_album_list_page(response_content['albums']['next'] + '&country=US', access_token)
    albums.extend(response_content['albums']['items'])

wanted_albums = []

for album in albums:
    if album['album_type'] != 'single':
        formatted_artists = []
        for artist in album['artists']:
            formatted_artists.append({
                'name': artist['name']
            })
        formatted_album = {
            'artists': formatted_artists,
            'external_urls': album['external_urls'],
            'name': album['name'],
            'release_date': album['release_date'],
            'total_tracks': album['total_tracks']
        }
        wanted_albums.append(formatted_album)

message_body = ''

for album in wanted_albums:
    message_body += email_object_to_string(album)

msg = MIMEMultipart()
msg['From'] = from_email
msg['To'] = to_email
msg['Subject'] = 'Spotify Album Releases: ' + datetime.now().strftime("%Y-%m-%d")

msg.attach(MIMEText(message_body, 'plain'))

server = smtplib.SMTP('smtp.gmail.com', 587)
server.ehlo()
server.starttls()
server.login(from_email, from_email_password)
server.sendmail(from_email, [to_email], msg.as_string())
server.quit()
