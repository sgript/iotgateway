'''
__author__ = "sgript"

Authentication code for clients connecting to gateway via pubnub
'''
# TODO: Implement some channel for global announcements to all devices
# .
# .
# TODO: Clean up code.

# # #

import string
import random
import json
import time
import hashlib
import gateway_database
import gateway_receiver

import logging
import pubnub
from pubnub.callbacks import SubscribeCallback
from pubnub.enums import PNStatusCategory
from pubnub.pnconfiguration import PNConfiguration, PNReconnectionPolicy
from pubnub.pubnub import PubNub

#pubnub.set_stream_logger('pubnub', logging.DEBUG) # Verbose, need only when required.
pnconfig = PNConfiguration()

pnconfig.subscribe_key = 'sub-c-12c2dd92-860f-11e7-8979-5e3a640e5579'
pnconfig.publish_key = 'pub-c-85d5e576-5d92-48b0-af83-b47a7f21739f'
pnconfig.secret_key = 'sec-c-YmZlMzkyYTctZDg1NC00ZTY0LWE3YzctNTkzOGRjZjk0OTI5'
pnconfig.subscribe_timeout = 9^99
pnconfig.connect_timeout = 9^99
pnconfig.non_subscribe_timeout = 9^99
pnconfig.ssl = True
pnconfig.reconnect_policy = PNReconnectionPolicy.LINEAR
pnconfig.uuid = 'GA'

pubnub = PubNub(pnconfig)

def id_generator(size=10, chars=string.ascii_uppercase + string.digits): # https://stackoverflow.com/a/2257449
    return ''.join(random.choice(chars) for _ in range(size))

def my_publish_callback(envelope, status):
    if not status.is_error():
        print("GatewayAuth: Message successfully sent to client.")
    else:
        print("GatewayAuth: Error transmitting message to client.")

class MySubscribeCallback(SubscribeCallback):

    def __init__(self):
        password = input("Database password: ")
        host = 'ephesus.cs.cf.ac.uk'
        user = 'c1312433'
        database = 'c1312433'

        print("GatewayAuth: Starting gateway database..")
        self.gd = gateway_database.GatewayDatabase(host, user, password, database)

        print("GatewayAuth: Starting the receiver..")
        self.gr = gateway_receiver.Receiver() # We could pass params however we want GR to be independent.

        self.receiver_auth_key = self.gd.receivers_key()

    def presence(self, pubnub, presence):

        if presence.event == "join":
            if presence.channel != "gateway_auth" and presence.uuid != presence.channel and presence.uuid != "GA":
                print('2. UNAUTHORISED USER ({}) HAS JOINED THE UUID CHANNEL ({}).\n\n\n'.format(presence.uuid, presence.channel))
                self.gd.auth_blacklist(presence.channel, presence.uuid)

            elif presence.channel == "gateway_auth" and presence.uuid != "GA":

                print("PRESENCE EVENT: " + str(presence.event))
                print("[1] UUID JOINED AUTH CHANNEL: {}".format(presence.uuid))

                pubnub.grant().channels(presence.uuid).read(True).write(True).sync()
                print("GatewayAuth: Connecting the UUID channel {}".format(presence.uuid))
                pubnub.subscribe().channels(presence.uuid).with_presence().execute()

                # Send hashed UUID over the gateway, client will know its UUID so it can hash and compute it.
                sha3_hash = hashlib.new("sha3_512")

                encode = sha3_hash.update((presence.uuid).encode("UTF-8"))
                pubnub.publish().channel('gateway_auth').message(sha3_hash.hexdigest()).async(my_publish_callback)

                # Check UUID channel info
                envelope = pubnub.here_now().channels(presence.uuid).include_uuids(True).include_state(True).sync()
                users_in_channel = envelope.result.total_occupancy

                # Someone could be spying - at this point only the gateway should be here.
                if users_in_channel > 1:
                    print("WARNING! Someone may be spying in the channel")
                    uuids_in_channel = []
                    users = envelope.result.channels[0].occupants

                    for occupant in users: # If there is indeed multiple people in the channel only then we bother to check who.
                        print(occupant.uuid) # - lists all uuids in channel, if more than one can later 'blacklist' ones not meant to be in the channel -> "do not serve, suspicious"

                        if occupant.uuid != "GA" and occupant.uuid != presence.uuid: # only blacklist if not gateway or the legit user
                            uuids_in_channel.append(occupant.uuid)
                            self.gd.auth_blacklist(presence.channel, occupant.uuid) # blacklist them

                    pubnub.publish().channel(presence.uuid).message(
                        {"error": "Too many occupants in channel, regenerate UUID."}).async(my_publish_callback)

            elif presence.channel != "gateway_auth" and presence.uuid == presence.channel: # uuid channel presence
                print('[2] REQUIRED USER ({}) HAS JOINED THE UUID CHANNEL ({}).'.format(presence.uuid, presence.channel))
                users_auth_key = id_generator()
                channelName = id_generator()

                # Send auth key to user
                pubnub.publish().channel(presence.uuid).message(
                    {"channel": channelName, "auth_key": users_auth_key}).async(my_publish_callback) # Send data over 1-1 channel

                # Grant + Subscribe to new private channel.
                pubnub.grant().channels([channelName]).auth_keys([users_auth_key, self.receiver_auth_key]).read(True).write(True).manage(True).ttl(0).sync()
                self.gr.subscribe_channel(channelName) # Receiver to subscribe to this private channel for function calls.

                print("GatewayAuth: Connecting to private channel {}..".format(channelName))
                pubnub.subscribe().channels(channelName).execute()
                self.gd.gateway_subscriptions(channelName, presence.uuid)

        if presence.event == "timeout" or presence.event == "leave" and presence.uuid != "GA":
            print("{} event on channel {}, unsubscribing.".format(presence.event, presence.channel))
            pubnub.unsubscribe().channels(presence.uuid).execute()

    def status(self, pubnub, status):
        if status.category == PNStatusCategory.PNUnexpectedDisconnectCategory:
            print("GatewayAuth: Unexpectedly disconnected.")

        elif status.category == PNStatusCategory.PNConnectedCategory:
            print("GatewayAuth: Connected.")

        elif status.category == PNStatusCategory.PNReconnectedCategory:
            print("GatewayAuth: Reconnected.")

    def message(self, pubnub, message):
        pass  # Handle new message stored in message.message

# Add listener to auth channel

if __name__ == "__main__":
    listener = MySubscribeCallback()
    pubnub.add_listener(listener)

    pubnub.grant().channels(["gateway_auth"]).read(True).write(True).manage(True).sync()
    print("GatewayAuth: Connecting to gateway channel..")
    pubnub.subscribe().channels(["gateway_auth"]).with_presence().execute()
