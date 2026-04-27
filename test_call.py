from twilio.rest import Client

account_sid = "AC5d486edbea3b01d871459ecc6ab2a509"
auth_token = "b6dd086fc852e89276e20b0a9f789244"

client = Client(account_sid, auth_token)

call = client.calls.create(
    to="+916392270722",
    from_="+12603005044",
    url="http://demo.twilio.com/docs/voice.xml"
)

print("Call SID:", call.sid)