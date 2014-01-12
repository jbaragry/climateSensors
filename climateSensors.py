# -*- coding: UTF-8 -*-

import sys, logging
import requests
from bs4 import BeautifulSoup as bs
import logging
import re
from datetime import datetime
import gspread
from ConfigParser import SafeConfigParser

num_verisure_sensors = 3
config_file = "./climateSensors.config"

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger('climateSensors')
config_parser = SafeConfigParser()

def get_verisure_sensor_data():
	payload = {
		'j_username':config_parser.get('verisure', 'verisure_username'),
		'j_password':config_parser.get('verisure', 'verisure_password'),
		'spring-security-redirect':'/no/start.html'
		}

	s = requests.Session()
	r1 = s.get('https://mypages.securitas-direct.com/login.html')
	r2 = s.post("https://mypages.securitas-direct.com/j_spring_security_check?locale=no_NO", data=payload)
	soup = bs(r2.text)
	sensors = soup.find_all(title=u'Røykdetektor')
	sensors_data = {}

	# find the timestamp for the sensors.
	# assumption is that they are all the same. raise exception later if they are not
	results = sensors[0].find_all('div', id=re.compile('^timestamp-'), limit=1)
	if (len(results) != 1):
			log.error('Sensor info\n', sensor)
			raise RuntimeError("expected at least 1 timestamp for but got ", len(results))
	ts = datetime.strptime(results[0].get_text(strip=True).split()[-1], '%H:%M')
	dt = datetime.combine(datetime.today().date(), ts.time())
	#print dt
	sensors_data['timestamp'] = dt
	
	if (len(sensors) != num_verisure_sensors):
		raise RuntimeError("serious problem with the XML I expected ", num_verisure_sensors, " sensors but only got ", len(sensors))
	for sensor in sensors:
		# get sensor location
		location = sensor.select("> span")[0].get_text()
		# get timestamp
		results = sensor.find_all('div', id=re.compile('^timestamp-'), limit=1)
		if (len(results) != 1):
			log.error('Sensor info\n', sensor)
			raise RuntimeError("expected 1 timestamp for ", location, " but got ", len(results))
		#timestamp = results[0].get_text(strip=True)
		ts = datetime.strptime(results[0].get_text(strip=True).split()[-1], '%H:%M')
		dts = datetime.combine(datetime.today().date(), ts.time())
		if (dts.date() != dt.date() and dts.time() != dt.time()):
			log.error('Timestamp info\n', sensor)
			raise RuntimeError("expected same timestamp for ", location, " but got ", dts)
		# get temperature
		results = sensor.find_all('span', id=re.compile('^temperature-'), limit=1)
		if (len(results) != 1):
			log.error('Sensor info\n', sensor)
			raise RuntimeError("expected 1 temperature for ", location, " but got ", len(results))
		temp = results[0].get_text(strip=True)
		# get rid of the % sign and change float format from norwegian so I can stick it in gdocs
		# should probably do this with locale module but its a bit heavyweight
		temp = temp.replace(u'\xb0', '')
		temp = temp.replace(',', '.')
		temp = float(temp)
		# get humidity
		results = sensor.find_all('span', id=re.compile('^humidity-'), limit=1)
		if (len(results) != 1):
			log.error('Sensor info\n', sensor)
			raise RuntimeError("expected 1 humidity for ", location, " but got ", len(results))
		humidity = results[0].get_text(strip=True)
		humidity = humidity.replace(',', '.')
		humidity = humidity.replace('%', '')
		humidity = float(humidity)
		sensors_data[location] = {'temperature': temp, 'humidity': humidity}
		print sensors_data[location]
	log.info("extracted following from verisure: ", sensors_data)
	return sensors_data

def save_sensor_data(sdata): 
	try:
		gc = gspread.login(config_parser.get('google_drive', 'gdrive_username'), config_parser.get('google_drive', 'gdrive_password'))
	except:
		print "Unable to log in.  Check your username/password"
 		log.error("Could not login to google drive")
 		raise RuntimeError("Could not login to google drive")

	try:
		sheet = gc.open(config_parser.get('google_drive', 'gdrive_spreadsheet')).sheet1
		sheet_data = [sdata['timestamp'], sdata['Stue']['temperature'], sdata['Stue']['humidity'], sdata['Kjellerstue']['temperature'], sdata['Kjellerstue']['humidity'], sdata['Sovegang']['temperature'], sdata['Sovegang']['humidity']]
		print sheet_data
		sheet.append_row(sheet_data)
	except:
  		log.error("Unable to open the spreadsheet.  Check your filename: ", gspreadsheet) 
  		raise RuntimeError("Could not open spreadsheet")

def get_config():
	try:
		if (len(config_parser.read(config_file)) != 1):
			raise RuntimeError("Could not read config file %s" % config_file)
	except:
		log.error("Could not read get config")
		raise RuntimeError("could not get config")

def main():
	try:
		get_config()
		sensors_data = get_verisure_sensor_data()
		print sensors_data
		save_sensor_data(sensors_data)
		return 0;
	except Exception, err:
		log.exception('Error: %s\n' % str(err))
	
if __name__ == '__main__':
	main()

