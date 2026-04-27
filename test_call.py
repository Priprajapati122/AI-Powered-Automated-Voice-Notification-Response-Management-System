from twilio.rest import Client

account_sid = "#########"
auth_token = "##########"

client = Client(account_sid, auth_token)

call = client.calls.create(
    to="#########",
    from_="#########",
    url="#############"
)

print("Call SID:", call.sid)
