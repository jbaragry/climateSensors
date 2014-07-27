#!/Library/Frameworks/Python.framework/Versions/2.7/bin/python
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

logging.basicConfig(level=logging.DEBUG)
config_parser = SafeConfigParser()

#log file hardcoded in same dir for now
logger = logging.getLogger(__name__)
logformatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
loghandler = logging.FileHandler('./climateSensors.log')
loghandler.setLevel(logging.INFO)
loghandler.setFormatter(logformatter)
logger.addHandler(loghandler)

dt_fmt = '%Y-%m-%d %H:%M'

def get_verisure_sensor_data():
	payload = {
		'j_username':config_parser.get('verisure', 'verisure_username'),
		'j_password':config_parser.get('verisure', 'verisure_password'),
		'spring-security-redirect':'/no/start.html'
		}

	s = requests.Session()
	r1 = s.get('https://mypages.verisure.com/no')
	r2 = s.post("https://mypages.verisure.com/j_spring_security_check?locale=no_NO", data=payload)
	r3 = s.get('https://mypages.verisure.com/no/start.html')
	soup = bs(r3.text)
	logger.debug(soup)
	sensors = soup.find_all(title=u'Røykdetektor')
	logger.debug(sensors)
	sensors_data = {}

	# find the timestamp for the sensors.
	# assumption is that they are all the same. raise exception later if they are not
	results = sensors[0].find_all('div', id=re.compile('^timestamp-'), limit=1)
	logger.debug(results)
	if (len(results) != 1):
			logger.error('Sensor info\n', sensor)
			raise RuntimeError("expected at least 1 timestamp for but got ", len(results))
	ts = datetime.strptime(results[0].get_text(strip=True).split()[-1], '%H:%M')
	dt = datetime.combine(datetime.today().date(), ts.time())
	ts_prev = config_parser.get('climateSensors', 'last_timestamp')
	if ts_prev >= dt.strftime(dt_fmt):
		logger.info('timestamp same as last time. exit')
		return []
	logger.debug('timestamp = %s', str(ts))
	config_parser.set('climateSensors', '# DO NOT CHANGE last_timestamp It is set by the script to keep track of the last sensore values reported by verisure', '')
	config_parser.set('climateSensors', 'last_timestamp', dt.strftime(dt_fmt))

	sensors_data['timestamp'] = dt.strftime(dt_fmt)
	
	if (len(sensors) != num_verisure_sensors):
		logger.error(soup)
		raise RuntimeError("serious problem with the XML I expected ", num_verisure_sensors, " sensors but only got ", len(sensors))
	for sensor in sensors:
		# get sensor location
		location = sensor.select("> span")[0].get_text()
		logger.info("got location: %s", location)
		# get timestamp
		results = sensor.find_all('div', id=re.compile('^timestamp-'), limit=1)
		if (len(results) != 1):
			logger.error('Sensor info\n', sensor)
			raise RuntimeError("expected 1 timestamp for ", location, " but got ", len(results))
		#timestamp = results[0].get_text(strip=True)
		ts = datetime.strptime(results[0].get_text(strip=True).split()[-1], '%H:%M')
		dts = datetime.combine(datetime.today().date(), ts.time())
		if (dts.date() != dt.date() and dts.time() != dt.time()):
			logger.error('Timestamp info\n', sensor)
			raise RuntimeError("expected same timestamp for ", location, " but got ", dts)
		# get temperature
		results = sensor.find_all('span', id=re.compile('^temperature-'), limit=1)
		if (len(results) != 1):
			logger.error('Sensor info\n', sensor)
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
			logger.error('Sensor info\n', sensor)
			raise RuntimeError("expected 1 humidity for ", location, " but got ", len(results))
		humidity = results[0].get_text(strip=True)
		humidity = humidity.replace(',', '.')
		humidity = humidity.replace('%', '')
		humidity = float(humidity)
		sensors_data[location] = {'temperature': temp, 'humidity': humidity}
		logger.debug(sensors_data[location])
	logger.info("extracted following from verisure: %s", str(sensors_data))
	return sensors_data

def save_sensor_data(sdata): 
	try:
		gc = gspread.login(config_parser.get('google_drive', 'gdrive_username'), config_parser.get('google_drive', 'gdrive_password'))
	except:
		logger.error("Unable to log in.  Check your username/password")
 		logger.error("Could not login to google drive")
 		raise RuntimeError("Could not login to google drive")

	try:
		sheet = gc.open(config_parser.get('google_drive', 'gdrive_spreadsheet')).sheet1
		sheet_data = [sdata['timestamp'], sdata['Stue']['temperature'], sdata['Stue']['humidity'], sdata['Kjellerstue']['temperature'], sdata['Kjellerstue']['humidity'], sdata['Sovegang']['temperature'], sdata['Sovegang']['humidity']]
		logger.info('Saving to gspread: %s', sheet_data)
		sheet.append_row(sheet_data)
	except:
  		logger.error("Unable to open the spreadsheet.  Check your filename: ", gspreadsheet) 
  		raise RuntimeError("Could not open spreadsheet")

def get_config():
	try:
		if (len(config_parser.read(config_file)) != 1):
			raise RuntimeError("Could not read config file %s" % config_file)
		
	except:
		logger.error("Could not read get config or logger")
		raise RuntimeError("could not get config or logger")

def update_config(): # add new timestamp to config file
	try:
		logger.debug('opening config file: %s', config_file)
		cfgfile = open(config_file, 'w')
		config_parser.write(cfgfile)
		cfgfile.close()
	except:
		raise

def main():
	try:
		logger.info("starting")
		get_config()
		sensors_data = get_verisure_sensor_data()
		if (sensors_data == {}):
			sys.exit()
		logger.info('got sensors_data: %s', str(sensors_data))
		save_sensor_data(sensors_data)
		update_config()
		return 0;
	except Exception, err:
		logger.exception('Error: %s\n' % str(err))
	
if __name__ == '__main__':
	main()

