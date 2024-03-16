import requests
from lxml import etree
import xml.etree.ElementTree as ET
import json
from bs4 import BeautifulSoup
from PIL import Image


class DLStatusCheck:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = 'https://parivahan.gov.in/'
        self.form_url = self.base_url + 'rcdlstatus/?pur_cd=101'
        self.form_data = {}

    def fetch_form(self):
        response = self.session.get(self.form_url)
        soup = BeautifulSoup(response.content, "html.parser")
        self.form = soup.find("form", id="form_rcdl")
        self.dl_no_field = self.form.find("input", id="form_rcdl:tf_dlNO")
        self.dob_field = self.form.find("input", id="form_rcdl:tf_dob_input")
        self.captcha_field = self.form.find("input", id="form_rcdl:j_idt31:CaptchaID")
        self.submit_button = self.form.find("button", id="form_rcdl:j_idt41")
        self.jfv = self.form.find("input", id="j_id1:javax.faces.ViewState:0")
        self.captcha_img = self.form.find("img", id="form_rcdl:j_idt31:j_idt36")

    def get_captcha(self):
        captcha_url = self.base_url + self.captcha_img["src"]
        img = Image.open(requests.get(captcha_url, stream=True).raw)
        img.show()

    def get_user_input(self):
        self.dl_no = input("Enter DL No: ")
        self.dob = input("Enter DOB (dd-mm-yyyy): ")
        self.captcha = input("Enter Captcha: ")

    def prepare_form_data(self):
        self.form_data = {
            "javax.faces.partial.ajax": "true",
            "javax.faces.source": self.submit_button["id"],
            "javax.faces.partial.execute": "@all",
            "javax.faces.partial.render": "form_rcdl:pnl_show form_rcdl:pg_show form_rcdl:rcdl_pnl",
            self.submit_button["id"]: self.submit_button["id"],
            self.form["id"]: self.form["id"],
            self.dl_no_field["name"]: self.dl_no,
            self.dob_field["name"]: self.dob,
            self.captcha_field["name"]: self.captcha,
            self.jfv["name"]: self.jfv["value"],
        }

    def post_form(self):
        post_url = self.base_url + self.form["action"]
        response = self.session.post(
            post_url, data=self.form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        if response.status_code != 200:
            print("Failed to fetch data. Please try again.")
            return

        soup = BeautifulSoup(response.content, features="xml").text

        parser = etree.HTMLParser()
        tree = etree.fromstring(str(soup), parser=parser)

        try:
            current_status = tree.xpath(
                "//table[@class='table table-responsive table-striped table-condensed table-bordered'][1]"
            )
            current_status = \
            etree.tostring(current_status[0], pretty_print=True).decode().split("""<td><span class="">""")[1].split(
                """</span></td>""")[0]
            details = tree.xpath(
                "//table[@class='table table-responsive table-striped table-condensed table-bordered'][1]/tr")
            initial_details = tree.xpath(
                "//table[@class='table table-responsive table-striped table-condensed table-bordered'][2]/tr")
            endorsed_details = tree.xpath(
                "//table[@class='table table-responsive table-striped table-condensed table-bordered'][3]/tr")

            validity_details_p1 = tree.xpath(
                "//table[@class='table table-responsive table-striped table-condensed table-bordered data-table'][1]")

            non_transport_from = etree.tostring(validity_details_p1[0][0], pretty_print=True).decode().split("""From: </span>""")[1].split("""</td>""")[0]
            non_transport_to = etree.tostring(validity_details_p1[0][0], pretty_print=True).decode().split("""To: </span>""")[1].split("""</td>""")[0]

            transport_from = etree.tostring(validity_details_p1[0][1], pretty_print=True).decode().split("""From: </span>""")[1].split("""</td>""")[0]
            transport_to = etree.tostring(validity_details_p1[0][1], pretty_print=True).decode().split("""To: </span>""")[1].split("""</td>""")[0]

            validity_details_p2 = tree.xpath(
                "//table[@class='table table-responsive table-striped table-condensed table-bordered data-table'][2]/tr")

            vehicle_class_details = tree.xpath(
                "//div[@id='form_rcdl:j_idt117']/div/table"
            )[0]

            class_of_vehicle_details = []
            for row in vehicle_class_details.xpath("tbody/tr"):
                cells = [cell.text for cell in row.xpath("td")]
                class_of_vehicle_details.append({
                    "cov_category": cells[0],
                    "class_of_vehicle": cells[1],
                    "cov_issue_date": cells[2]
                })

            # Parse data into a dictionary
            data = {
                "current_status": current_status,
                "holder_name": details[1][1].text.strip(),
                "old_new_dl_no": details[2][1].text.strip(),
                "source_of_data": details[3][1].text.strip(),
                "initial_issue_date": initial_details[0][1].text.strip(),
                "initial_issuing_office": initial_details[1][1].text.strip(),
                "last_endorsed_date": endorsed_details[0][1].text.strip(),
                "last_endorsed_office": endorsed_details[1][1].text.strip(),
                "last_completed_transaction": endorsed_details[2][1].text.strip(),
                "driving_license_validity_details": {
                    "non_transport": {
                        "valid_from": non_transport_from,
                        "valid_upto": non_transport_to,
                    },
                    "transport": {
                        "valid_from": transport_from,
                        "valid_upto": transport_to,
                    },
                },
                "hazardous_valid_till": validity_details_p2[0][1].text.strip(),
                "hill_valid_till": validity_details_p2[0][3].text.strip(),
                "class_of_vehicle_details": class_of_vehicle_details
            }

            # Convert dictionary to JSON
            json_data = json.dumps(data, indent=4)

            # Print the JSON object
            print(json_data)

        except:
            print("Invalid details or captcha. Please try again.")

        # print(etree.tostring(table[0], pretty_print=True).decode())
        # print(etree.tostring(initial_table[0], pretty_print=True).decode())
        # print(etree.tostring(endorsed_table[0], pretty_print=True).decode())
        # print(etree.tostring(validity_table_p1[0], pretty_print=True).decode())
        # print(etree.tostring(validity_table_p2[0], pretty_print=True).decode())


if __name__ == "__main__":
    checker = DLStatusCheck()
    checker.fetch_form()
    checker.get_captcha()
    checker.get_user_input()
    checker.prepare_form_data()
    checker.post_form()
