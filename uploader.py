CRM_URL="https://24568.zebracrm.com"
WATCH_DIR=r"C:\Dev\Personal\youtube-upload\watch"
UPLOADED_DIR=r"C:\Dev\Personal\youtube-upload\uploaded"
FAILED_DIR=r"C:\Dev\Personal\youtube-upload\failed"
URL_PROGRESS_STATUS="progress"
URL_SUCCESS_STATUS="success"
URL_FAILED_STATUS="failed"
VIDEO_TITLE="!%s - בצניחה חופשית מדהימה ב- הצנחניה | הנוף היפה בארץ"
# --------------------------------------------------------------------
import requests
from xml.etree import ElementTree
from youtube_upload import main
import time
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import shutil
import os

get_data_xml = """<ROOT>
	<PERMISSION>
		<USERNAME>API</USERNAME>
		<PASSWORD>Y852147</PASSWORD>
	</PERMISSION>
	<FILTERS>
		<CAMPAIGN/>
	</FILTERS>
	<FOCUSE_FILTER>
		<FOCUS></FOCUS>
	</FOCUSE_FILTER>
	<FIELDS>
		<F_N/>
		<P_N/>
		<TID/>
		<jump_date/>
		<Youtube/>
		<urlstat/>
	</FIELDS>
	<FOCUSES>
		<FOCUS>
			<KEY></KEY>
			<STATUS/>
			<UPDATE_DATE/>
		</FOCUS>
	</FOCUSES>
	<ID/>
	<CARD_TYPE/>
	<ID_FILTER>%s</ID_FILTER>
	<CARD_TYPE_FILTER></CARD_TYPE_FILTER>
</ROOT>"""

update_data_xml = """<?xml version="1.0" encoding="utf-8"?>
<ROOT>
	<PERMISSION>
		<USERNAME>API</USERNAME>
		<PASSWORD>Y852147</PASSWORD>
	</PERMISSION>
	<CARD_TYPE>Tandems</CARD_TYPE>
	<IDENTIFIER>
		<ID>%s</ID>
	</IDENTIFIER>
	<CUST_DETAILS>
		<Youtube>%s</Youtube>
		<urlstat>%s</urlstat>
	</CUST_DETAILS>
</ROOT>"""
headers = {'Content-Type': 'application/xml'} # set what your server accepts
get_data_uri= CRM_URL + "/ext_interface.php?b=get_multi_cards_details"
update_date_uri = CRM_URL + "/ext_interface.php?b=update_customer"


def move_to_dir(file_path, dest):
    try:
        shutil.move(file_path, dest)
        print("file \"%s\" moved to %s" % (file_path, dest))
    except Exception as e:
        print("Failed to move file %s to %s\n%s" % (file_path, dest, str(e)))

def handle_file(event):
    if event.event_type == "created":
        file_path = event.src_path
    else:
        file_path = event.dest_path
    user_id = os.path.splitext(os.path.basename(file_path))[0]
    print("Handling user_id: " + user_id)
    body = get_data_xml % user_id
    customer_data = requests.post(get_data_uri, data=body, headers=headers)

    root = ElementTree.fromstring(customer_data.content)
    cards = root.findall("./result/CARDS")
    if len(cards) != 1:
        print("ERROR - more than one cards were returend from CRM")
    else:
        title =  VIDEO_TITLE % root.find("./result/CARDS/CARD/FIELDS/P_N").text
        body = update_data_xml % (user_id, "", URL_PROGRESS_STATUS)
        requests.post(update_date_uri, data=body, headers=headers)
        try:
            video_url = main.main(["--client-secrets=client_secrets.json", "--title=" + title, file_path])
            if video_url is not None:
                body = update_data_xml % (user_id, video_url, URL_SUCCESS_STATUS)
                requests.post(update_date_uri, data=body, headers=headers)
                move_to_dir(file_path, UPLOADED_DIR)
            else:
                body = update_data_xml % (user_id, "", URL_FAILED_STATUS)
                move_to_dir(file_path, FAILED_DIR)
                requests.post(update_date_uri, data=body, headers=headers)
        except Exception as e:
            print("Failed to upload video: " + str(e))
            move_to_dir(file_path, FAILED_DIR)
            body = update_data_xml % (user_id, "", URL_FAILED_STATUS)
            try:
                requests.post(update_date_uri, data=body, headers=headers)
            except:
                print("Failed to update CRM")
    print("Handler finished")


if __name__ == "__main__":
    patterns = "*"
    ignore_patterns = ""
    ignore_directories = False
    case_sensitive = True
    my_event_handler = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)
    my_event_handler.on_moved = handle_file
    my_event_handler.on_created = handle_file

    path = WATCH_DIR
    go_recursively = True
    my_observer = Observer()
    my_observer.schedule(my_event_handler, path, recursive=go_recursively)
    my_observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        my_observer.stop()
        my_observer.join()
