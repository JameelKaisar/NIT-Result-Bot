# NIT Srinagar Result Bot (NIT-Result-Bot)
# Created by Jameel Kaisar (Ajmi)
# July 13, 2021



from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler, CallbackQueryHandler

import cv2
import numpy as np
import pytesseract
import re
from unidecode import unidecode

import os

from urllib.request import Request, urlopen, urlretrieve
from urllib.parse import urlencode
from urllib.error import HTTPError
from collections import Counter
from bs4 import BeautifulSoup



BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = os.environ["ADMIN_ID"]
LINK = "https://result.nitsri.ac.in/"



def get_semesters(student):
  for limit in range(3):
    try:
      data = {
        "__VIEWSTATE": "/wEPDwUKLTE3ODk4NzY1Mg9kFgICAQ9kFgQCCQ8QZGQWAWZkAh8PDxYCHgdWaXNpYmxlaGQWBAIPDxQrAAIPFgQeC18hRGF0YUJvdW5kZx4LXyFJdGVtQ291bnQC/////w9kZGQCEQ8PFgIeBFRleHRlZGQYAwUeX19Db250cm9sc1JlcXVpcmVQb3N0QmFja0tleV9fFgQFCmJ0bmltZ1Nob3cFEGJ0bmltZ1Nob3dSZXN1bHQFCGJ0blByaW50BQxidG5pbWdDYW5jZWwFEGx2U3ViamVjdERldGFpbHMPZ2QFCENhcHRjaGExDwUkNGRlNDVhNGMtOTIyYi00MTM1LWFkZTgtZjhkMzczNDZlZThmZNEFjPN4CBwfLWWlZjINWo62U4wgslxqQhHHOsA6Flw+",
        "btnimgShow.x": "32",
        "btnimgShow.y": "15",
        "txtRegno": student
      }
      with urlopen(Request(LINK, data=urlencode(data).encode())) as response:
        source = response.read().decode()
      soup = BeautifulSoup(source, 'html.parser')
      semesters = [(x.get('value'), x.getText()) for x in soup.find('select', {'id': 'ddlSemester'}).find_all('option')[1:]]
      id = soup.find('input', {'id': 'hfIdno'}).get('value')
      viewstate = soup.find('input', {'id': '__VIEWSTATE'}).get('value')
      captcha = soup.find('img', {'width': '200'}).get('src')
      return semesters, id, viewstate, captcha
    except:
      pass
  return None, None, None, None


def get_captcha(src):
  img = cv2.imread(src)

  hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
  mask = cv2.inRange(hsv, (36, 25, 25), (70, 255,255))
  imask = mask > 0
  green = np.zeros_like(img, np.uint8)
  green[imask] = img[imask]

  h,w,bpp = np.shape(green)
  for py in range(0, h):
    for px in range(0, w):
      if ( green[py][px][0] < 100 and green[py][px][1] < 100 and green[py][px][2] < 100):
        green[py][px] = (255, 255, 255)

  custom_config = r'-l eng --oem 3 --psm 7 -c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"'
  text = pytesseract.image_to_string(green, config=custom_config)
  text = re.sub(r'\W+', '', unidecode(text)).upper()

  return text


def get_result(context):
  for limit in range(3):
    try:
      data = {
        "__VIEWSTATE": context['viewstate'],
        "txtRegno": context['student'],
        "hfIdno": context['id'],
        "ddlSemester": context['semester'],
        "txtCaptcha": "XXXXX",
        "btnimgShowResult.x": "40",
        "btnimgShowResult.y": "11"
      }

      decoder = {}
      url = LINK + context['captcha']
      for _ in range(5):
        try:
          src = f"/app/Captcha/Captcha_{context['student']}_{context['semester']}.jfif"
          urlretrieve(url, src)
          text = get_captcha(src)
          os.remove(src)
          for i in range(len(text)):
            if i not in decoder:
              decoder[i] = []
            decoder[i].append(text[i])
        except HTTPError:
          with urlopen(Request(LINK, data=urlencode(data).encode())) as response:
            source = response.read().decode(errors='ignore')
          soup = BeautifulSoup(source, 'html.parser')
          raise
        except:
          continue
      text = ''
      for i in range(5):
        text += max(decoder[i], key=Counter(decoder[i]).get)
      data['txtCaptcha'] = text

      with urlopen(Request(LINK, data=urlencode(data).encode())) as response:
        source = response.read().decode(errors='ignore')
      soup = BeautifulSoup(source, 'html.parser')
      html = soup.find('div', {'id': 'PnlShowResult'})
      if html == None:
        raise
      
      result_student = {"Session": html.find('span', {'id': 'lblSession'}).getText(), "Name": html.find('span', {'id': 'lblStudent'}).getText(), "Enrollment": html.find('span', {'id': 'lblRollno'}).getText(), "Semester": html.find('span', {'id': 'lblSemester'}).getText(), "Degree": html.find('span', {'id': 'lbldegree'}).getText(), "Branch": html.find('span', {'id': 'lblbranch'}).getText(), "Publish Date": html.find('span', {'id': 'lblPublishDate'}).getText(), "Semester Credits": html.find('span', {'id': 'lblearn'}).getText(), "Semester Grade Points": html.find('span', {'id': 'lblgd'}).getText(), "SGPA": html.find('span', {'id': 'lblSgpa'}).getText(), "Cumulative Credits": html.find('span', {'id': 'lblearn1'}).getText(), "Cumulative Grade Points": html.find('span', {'id': 'lblgd1'}).getText(), "CGPA": html.find('span', {'id': 'lblSgpa1'}).getText(), "Result": html.find('span', {'id': 'lblresult'}).getText()}
      subject_keys = ["Name", "Grade", "Credits"]
      subject_result = {}

      for subject in html.find_all('table', {'class': 'table-data'})[1].find_all('tr')[1:]:
        subject_values = [x.getText().strip() for x in subject.find_all('td')]
        subject_result[subject_values[0]] = {}
        for i, j in zip(subject_keys, subject_values[1:]):
          subject_result[subject_values[0]][i] = j
      result_student['Subjects'] = subject_result

      return result_student
    except:
      if 'source' in locals() and 'soup' in locals() and soup is not None:
        context['viewstate'] = soup.find('input', {'id': '__VIEWSTATE'}).get('value')
        context['captcha'] = soup.find('img', {'width': '200'}).get('src')
  return None



def start(update: Update, context: CallbackContext) -> None:
  user = update.effective_user
  update.message.reply_markdown(f"Hi [{user.first_name}](tg://user?id={user.id})!\n\nSend your Enrollment Number to see the Result!")


def admin(update: Update, context: CallbackContext) -> None:
  user = update.effective_user
  if str(user.id) == ADMIN_ID:
    update.message.reply_text("You are Admin!", reply_to_message_id=update.message.message_id)
  else:
    update.message.reply_text("You are not authorised to use this command!", reply_to_message_id=update.message.message_id)


def help_command(update: Update, context: CallbackContext) -> None:
  update.message.reply_markdown("*Help Menu:*\n\nGet Result:\n`/result enrollment_num`\n\nGet Result PDF:\n`/pdf enrollment_num`\n\nGet Result Screenshot:\n`/ss enrollment_num`\n\nHelp Menu:\n`/help`\n\nAbout this Bot:\n`/about`\n\n*Example:*\n`/result 2020BITE001`")


def about(update: Update, context: CallbackContext) -> None:
  update.message.reply_markdown(f"*About this Bot:*\n\nLanguage: Python\n\nLibraries: Python Telegram Bot, Selenium, Chromium, PyTesseract, OpenCV, NumPy and Unidecode\n\nInitial Release: July 8, 2021\n\nCreator: [Jameel Kaisar](tg://user?id={ADMIN_ID}) (_Ajmi_)\n\nBatch: IT 2020 (2020BITE001)\n\nSource Code: [GitHub](https://github.com/JameelKaisar/NIT-Result-Bot)")


def command(update: Update, context: CallbackContext) -> None:
  update.message.reply_text("Invalid Command!", reply_to_message_id=update.message.message_id)


def others(update: Update, context: CallbackContext) -> None:
  update.message.reply_text("Invalid Input!", reply_to_message_id=update.message.message_id)


def result(update: Update, context: CallbackContext) -> None:
  temp = update.message.reply_text("Checking Enrollment Number... Please Wait...")
  if update.message.text.startswith('/result'):
    context.user_data['mode'] = 'result'
    context.user_data['student'] = update.message.text.replace('/result ', '')
  elif update.message.text.startswith('/pdf'):
    temp.delete()
    update.message.reply_text("This Command will be Available Soon!")
    return ConversationHandler.END
    context.user_data['mode'] = 'pdf'
    context.user_data['student'] = update.message.text.replace('/pdf ', '')
  elif update.message.text.startswith('/ss'):
    temp.delete()
    update.message.reply_text("This Command will be Available Soon!")
    return ConversationHandler.END
    context.user_data['mode'] = 'ss'
    context.user_data['student'] = update.message.text.replace('/ss ', '')
  else:
    context.user_data['mode'] = 'direct'
    context.user_data['student'] = update.message.text
  semesters, id, viewstate, captcha = get_semesters(context.user_data['student'])
  temp.delete()
  if semesters == None or semesters == []:
    update.message.reply_text("Student Not Available or Result Yet to be Published!")
    return ConversationHandler.END
  semesters_dict = {}
  for i, j in semesters:
    semesters_dict[i] = j.title()
  context.user_data['semesters'] = semesters_dict
  context.user_data['id'] = id
  context.user_data['viewstate'] = viewstate
  context.user_data['captcha'] = captcha
  keyboard = [[InlineKeyboardButton(y, callback_data=x)] for x, y in semesters_dict.items()]
  keyboard.append([InlineKeyboardButton("Cancel", callback_data="0")])
  reply_markup = InlineKeyboardMarkup(keyboard)
  context.user_data['message'] = update.message.reply_text("Select Semester:", reply_markup=reply_markup)


def semester(update: Update, context: CallbackContext) -> None:
  query = update.callback_query
  try:
    query.answer()
  except Exception as err:
    print(f"{type(err).__name__}: {err}")
  context.user_data['semester'] = query.data
  if query.data == '0':
    query.edit_message_text(text="Cancelled!")
  else:
    query.edit_message_text(text=f"Selected Option: {context.user_data['semesters'][query.data]}\n\nFetching Result... Please be Patient...")
    result_data = get_result(context.user_data)
    context.user_data['message'].delete()
    if result_data == None:
      query.message.reply_markdown(text="Unable to fetch the result! Please try again!")
      return None
    subjects = "*Subjects:*"
    for i, j in result_data['Subjects'].items():
      subjects += f"\n\n{j['Name']} ({i}):\nCredits: {j['Credits']}\nGrade: {j['Grade']}"
    query.message.reply_markdown(text=f"*Student Information:*\n\nName: {result_data['Name'].title()}\nEnrollment: {result_data['Enrollment']}\nDegree: {result_data['Degree'].replace('.', '. ').title()}\nBranch: {result_data['Branch']}\nSemester: {result_data['Semester'].title()}\nSession: {result_data['Session'].title()}\nPublish Date: {result_data['Publish Date']}\n\n\n{subjects}\n\n\n*Overall Performance:*\n\nSemester Credits: {result_data['Semester Credits']}\nSemester Grade Points: {result_data['Semester Grade Points']}\nSGPA: {result_data['SGPA']}\n\nCumulative Credits: {result_data['Cumulative Credits']}\nCumulative Grade Points: {result_data['Cumulative Grade Points']}\nCGPA: {result_data['CGPA']}\n\nResult: *{result_data['Result']}*")



try:
  if not os.path.exists("/app/Captcha"):
    os.makedirs("/app/Captcha")
except:
  raise("Bot Not Deployed!")



updater = Updater(BOT_TOKEN)
dispatcher = updater.dispatcher

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("admin", admin))
dispatcher.add_handler(CommandHandler("help", help_command))
dispatcher.add_handler(CommandHandler("about", about))

dispatcher.add_handler(CommandHandler('result', result))
dispatcher.add_handler(CommandHandler('pdf', result))
dispatcher.add_handler(CommandHandler('ss', result))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, result))
dispatcher.add_handler(CallbackQueryHandler(semester))

dispatcher.add_handler(MessageHandler(Filters.command, command))
dispatcher.add_handler(MessageHandler(Filters.all, others))



updater.start_polling()
updater.idle()
