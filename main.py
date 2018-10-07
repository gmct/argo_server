from flask import Flask, request, redirect
from twilio.twiml.messaging_response import Message, MessagingResponse
import dialogflow
import pymysql
import requests
import os
import io

DIALOGFLOW_ID='argo-8d798'
os.environ["GOOGLE_APPLICATION_CREDENTIALS"]="Argo-96e8785e135c.json"
app = Flask(__name__)

def detect_labels(path):
    """Detects labels in the file."""
    from google.cloud import vision
    client = vision.ImageAnnotatorClient()

    with io.open(path, 'rb') as image_file:
        content = image_file.read()

    image = vision.types.Image(content=content)

    response = client.label_detection(image=image)
    labels = response.label_annotations
    print('Labels:')

    return labels
        
def detect_intent_texts(project_id, session_id, text, language_code):
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(project_id, session_id)

    if text:
        text_input = dialogflow.types.TextInput(
            text=text, language_code=language_code)
        query_input = dialogflow.types.QueryInput(text=text_input)
        response = session_client.detect_intent(
            session=session, query_input=query_input)

        return response.query_result.fulfillment_text
        
@app.route("/sms", methods=['GET', 'POST'])
def message_response():
    """Respond to incoming messages with a friendly SMS."""
    resp = MessagingResponse()
    print(request.form)
    if request.form['NumMedia'] == '0':
        message = request.form['Body']
        print(message)
        fulfillment_text = detect_intent_texts(DIALOGFLOW_ID, "unicornman", message, 'en')
        resp.message(fulfillment_text)
    else:
        if request.form['MediaContentType0'] == 'image/jpeg':
            extension = '.jpg'
        elif request.form['MediaContentType0'] == 'image/png':
            extension = '.png'
        else:
            resp.message("Unable to recognize media format. Please send a jpeg or png image.")
            return str(resp)
        filename = request.form['MessageSid'] + extension
        with open('{}/{}'.format('..', filename), 'wb') as f:
            image_url = request.form['MediaUrl0']
            f.write(requests.get(image_url).content)
        
        file_name = '../' + filename
        image_labels = detect_labels(file_name)
        descriptions = []
        for label in image_labels:
            descriptions.append(label.description)
        print(descriptions)
        
        #Sends data to db
        conn = pymysql.connect(host='35.188.173.100', port=3306, user='sidharth', passwd=None, db='db1')
        cur = conn.cursor()
        cmd_string = 'insert into images2(name,url,labels,from_,image_text) values("' + filename + '","' + request.form['MediaUrl0'] + '","' + ','.join(descriptions) + '","' + request.form['From'] + '","' + request.form['Body'] + '")'
        print(cmd_string)
        cur.execute(cmd_string)
        conn.commit()
        cur.close()
        
        resp.message('Your issue has been registered and will be investigated as soon as possible.' + descriptions[0])
    return str(resp)
if __name__ == "__main__":
    app.run(debug=True)