
import requests


url = "http://localhost/W-AccessAPI/v1/"
h = { 'WAccessAuthentication': 'usr:pwd', 'WAccessUtcOffset': '-180' }


def assign_card(cardholder):
    print("\n* Card - Get by ClearCode")
    card = None
    reply = requests.get(url + 'cards', headers=h, params = (("ClearCode", str(cardholder["CHID"])),))
    reply_json = reply.json()
    ## Version 4.205 or older
    try:
        if reply.status_code == requests.codes.ok:
            print("\n* Found Card: %s %s"%(reply_json["CardID"], reply_json["CardEndValidityDateTime"]))
            card = reply_json
        elif reply.status_code == requests.codes.not_found:
            print("Card not found")
        else:
            print("Error: " + reply_json["Message"])
    ## Version 4.206 or newer
    except:
        for wxs_card in reply_json:
            if reply.status_code == requests.codes.ok:
                print("\n* Found Card: %s %s"%(wxs_card["CardID"], wxs_card["CardEndValidityDateTime"]))
                card = wxs_card
            elif reply.status_code == requests.codes.not_found:
                print("Card not found")
            else:
                print("Error: " + wxs_card["Message"])


    if card and card["CHID"]:
        print("\n* Card is assigned. Unassigning it")
        reply = requests.delete(url + 'cardholders/%d/cards/%d'%(card["CHID"], card["CardID"]), json=card, headers=h)
        if reply.status_code == requests.codes.no_content:
            print("Card unassigned")
        elif reply.status_code == requests.codes.not_found:
            print("Card not found for unassign")
        else:
            print("Error: " + reply.json()["Message"])


    if card:
        print("\n* Card - Delete")
        reply = requests.delete(url + 'cards', headers=h, params = (("ClearCode",str(cardholder["CHID"])),))
        if reply.status_code == requests.codes.no_content:
            print("Card Deleted")
        elif reply.status_code == requests.codes.not_found:
            print("Card not found for deletion")
        else:
            reply_json = reply.json()
            print("Error: " + reply.json()["Message"])
        card = None


    if not card:
        print("\n* Card - Create resident card (CardType = 0)")
        new_card = { "ClearCode": str(cardholder["CHID"]), "CardNumber": cardholder["CHID"], "PartitionID": 0, "CardType" : 0 }
        reply = requests.post(url + 'cards', json=new_card, headers=h)
        reply_json = reply.json()
        if reply.status_code == requests.codes.created:
            card = reply_json
            print("New CardID: %d"%(card["CardID"]))
        else:
            print("Error: " + reply_json["Message"])


    if card:
        print("\n* Card - Assign to Cardholder")
        #card["CardEndValidityDateTime"] = "2016-01-01T10:00:00"
        reply = requests.post(url + 'cardholders/%d/cards'%(cardholder["CHID"]), json=card, headers=h)
        reply_json = reply.json()
        if reply.status_code == requests.codes.created:
            card = reply_json
            print("Card assigned")
            print("%s %s"%(card["CardID"], card["CardEndValidityDateTime"]))
        else:
            print("Error: " + reply_json["Message"])