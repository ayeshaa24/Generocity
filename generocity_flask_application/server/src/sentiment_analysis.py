# Call to the Natural language API for Sentiment Analysis

# Import the google cloud client libraries
from google.cloud import language
from google.cloud.language import types # types module contains classes for creating requests
from google.cloud.language import enums
import os
from keypath import keypath

def analyse_text(project_description_input):
    location = os.path.join(keypath,'keys.json')
    client = language.LanguageServiceClient.from_service_account_json(location)
    document = types.Document(content=project_description_input, type=enums.Document.Type.PLAIN_TEXT)
    annotations = client.analyze_sentiment(document=document)
    score = annotations.document_sentiment.score
    print("Overall Sentiment: score of ",score)
    output = int((50*score)+50)
    return output
