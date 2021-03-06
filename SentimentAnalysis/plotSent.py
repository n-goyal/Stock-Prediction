import matplotlib.pyplot as plt
import pandas as pd
import datetime
from textblob import TextBlob
from langdetect import detect
import numpy as np
import sys , getopt

# from configuring import *	
from configuring import inputFileDJIA , outputFileDJIA , inputFileTwitter , intermediateFileTwitter , outputFileTwitter , doTwitterPreprocessing , doDJIAPreprocessing , PlotGraphs 

def configurables(TwitterIntermediate,TwitterOutput,threshold=0.1,ZScaling=7.5):
	sentimentDataset = pd.read_csv(TwitterIntermediate,encoding='utf-8',error_bad_lines=False,low_memory=False)
	sentimentDataset = sentimentDataset[sentimentDataset['subjectivity'] > threshold ]

	# Calculating Z-Scores
	mu = sentimentDataset['polarity'].mean()
	std = sentimentDataset['polarity'].std()

	sentimentDataset['Z Score'] = ZScaling*(sentimentDataset['polarity'] - mu)/std
	
	sentimentDataset.to_csv(TwitterOutput, encoding='utf-8')
	print("Output File Generated at:",TwitterOutput)


def prepare_data( TwitterInput , TwitterIntermediate ):
	
	#Reading File
	sentimentDataset = pd.read_csv(TwitterInput,encoding='utf-8',error_bad_lines=False,low_memory=False,index_col=None)

	# Making a new column for grouping and Sorting according to DateTime
	sentimentDataset.rename(columns={"date":"DateTime"},inplace=True)
	sentimentDataset['DateTime'] = pd.to_datetime(sentimentDataset['DateTime'])
	sentimentDataset['Date'] = sentimentDataset['DateTime'].dt.date
	sentimentDataset.sort_values(by='DateTime',inplace=True)
	sentimentDataset.reset_index()

	print("The Shape of the file now is:",sentimentDataset.shape)


	#Finding Sentiment and making a new column for polarity and language
	print(sentimentDataset.head)

	for index , rows in sentimentDataset.iterrows(): 	
		try:
			text = rows['text']
			date = rows['Date']

			lang = detect(text)
			sentimentDataset.loc[index,'lang'] = lang

			analysis = TextBlob(text)
			polarity = analysis.sentiment[0]
			subjectivity = analysis.sentiment[1]
			sentimentDataset.loc[index,'polarity'] = polarity
			sentimentDataset.loc[index,'subjectivity'] = subjectivity

			day = date.strftime("%A")
			sentimentDataset.loc[index,'Day'] = day
			sentimentDataset.loc[index,'Date'] = date

			if index % 500 is 0:
				print("On row: ",index)
				print(text)
				print("Sentiment:\tPolarity"+str(sentimentDataset.loc[index,'polarity'])+"\tSubjectivity:"+str(sentimentDataset.loc[index,'subjectivity']))
				print("Day is:",sentimentDataset.loc[index,'Day'],"on:",sentimentDataset.loc[index,'Date'])
				print("\n\n")

		except Exception as e:
			print("Following Exception occured")
			print("\n"*2 + e + "\n"*2)
			continue


	sentimentDataset.sort_values(by='Date',inplace=True)

	sentimentDataset = sentimentDataset[['Date','Day','text','lang','polarity','subjectivity']]
	sentimentDataset.drop_duplicates(subset=['text'],inplace=True)


	# removing non-english tweets and writing to the output file
	sentimentDataset.dropna()
	sentimentDataset = sentimentDataset[sentimentDataset['lang'] == 'en']
	sentimentDataset = sentimentDataset[sentimentDataset['Day'] != 'Sunday']
	sentimentDataset = sentimentDataset[sentimentDataset['Day'] != 'Saturday']
	sentimentDataset = sentimentDataset[~( sentimentDataset['text'].str.contains('http') | sentimentDataset['text'].str.contains('https') )]
	sentimentDataset.set_index('Date',inplace=True)
	
	#Generating output
	print("Shape of Dataset Now is:",sentimentDataset.shape)
	sentimentDataset.to_csv(TwitterIntermediate, encoding='utf-8')
	print("intermediate File Generated at:",TwitterIntermediate)

	print(sentimentDataset)
	

def plot_all( company , sentimentDataset , DJIA ):
	DJIAdateList = DJIA['Date']
	sentimentDataset = sentimentDataset[sentimentDataset['Date'].isin(DJIAdateList)]
	sentimentPlot = sentimentDataset.groupby(['Date'])['Z Score'].mean().to_frame()


	print(sentimentPlot)

	# Plotting
	plt.figure(company)

	plt.plot(DJIA['Date'],DJIA['Z Score'],sentimentPlot)
	plt.plot(sentimentPlot)

	plt.xticks(rotation=30)
	plt.ylabel('Z-Scores')
	plt.legend(['DJIA','Sentiment'],loc='best')
	plt.title('Sentiment and DJIA Z-Scores vs Date')

	plt.show()



def write_DJIA_Z_scores(DJIAinput,DJIAoutput):
	DJIA = pd.read_csv(DJIAinput,low_memory=False,encoding='ISO-8859-1',error_bad_lines=False)	
	mu = DJIA['Adj Close'].mean()
	std = DJIA['Adj Close'].std()
	DJIA['Z Score'] = (DJIA['Adj Close'] - mu)/std
	DJIA['Date'] = pd.to_datetime(DJIA['Date'])

	DJIA.to_csv(DJIAoutput,index=False)

	return DJIA


def run( configure , company = 'Accenture' , doTwitterPreprocessing = True , doDJIAPreprocessing = True , PlotGraphs = True ):

	#DJIA files
	DJIAinput = inputFileDJIA.format(company)
	DJIAoutput = outputFileDJIA.format(company)

	if doDJIAPreprocessing == True:
		print("Preparing DJIA...")
		write_DJIA_Z_scores(DJIAinput,DJIAoutput)
	
	DJIA = pd.read_csv(DJIAoutput, encoding='utf-8',error_bad_lines=False,low_memory=False)


	# Twitter files
	TwitterInput = inputFileTwitter.format(company)
	TwitterIntermediate = intermediateFileTwitter.format(company)
	TwitterOutput = outputFileTwitter.format(company)


	if doTwitterPreprocessing == True:
		print("Preparing twitter data...")
		prepare_data(TwitterInput , TwitterIntermediate)

	
	if PlotGraphs == True:
		print("Plotting...")
		threshold , ZScaling = configure['threshold'] , configure['ZScaling']
		configurables(TwitterIntermediate,TwitterOutput,threshold,ZScaling)
		sentimentDataset = pd.read_csv(TwitterOutput, encoding='utf-8',error_bad_lines=False,low_memory=False )
		plot_all(company,sentimentDataset,DJIA)


def main(argv):
	configure = {}

	configure['ZScaling'] , configure['threshold'] = 7.5 , 0.1

	try:
		opts, args = getopt.getopt(argv, "", ("company=", "Zscale=", "threshold="))
		
	except getopt.GetoptError:
		print('plotSent.py --company <company-name> --Zscale <z-scaling-factor> --threshold <subjectivity-threshold>')
		sys.exit(2)


	for opt, arg in opts:
		if opt == '--h' or opt == '-h':
			print('plotSent.py --Zscale <z-scaling-factor> --threshold <subjectivity-threshold>')
			sys.exit()
		elif opt == "--company":
			company = arg
		elif opt == "--Zscale":
			print("here")
			configure['ZScaling'] = float(arg)
		elif opt == "--threshold":
			configure['threshold'] = float(arg)

	try:
		run(configure=configure,company=company,doTwitterPreprocessing=doTwitterPreprocessing,doDJIAPreprocessing=doDJIAPreprocessing,PlotGraphs=PlotGraphs)
	except Exception as e:
		print("The Following Exception occured:")
		print('\n'*2)
		print(e)
		print('\n'*2)
		print("Please Check the parameters provided.")
		print("Something wrong with parameters.")
		print("Running with default parameters.")
		print("Company: ",'Accenture')
		print("ZScaling: ",configure['ZScaling'])
		print("threshold: ",configure['threshold'])
		
		try:
			run(configure=configure,doTwitterPreprocessing=doTwitterPreprocessing,doDJIAPreprocessing=doDJIAPreprocessing,PlotGraphs=PlotGraphs)
		except:
			print("Please provide the company-name")


if __name__ == '__main__':
	main(sys.argv[1:])