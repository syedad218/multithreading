
# Import liraries
import sys
from operator import itemgetter
from multiprocessing import Pool
import time
import logging
from comparisons import *
import bottle
from bottle import post,get,run,route,request,hook,response,static_file
from corpus import *
from DButils import *
from dataSourceUtils import *
from sales import fetch_stock
#from payment import *
from trading import *
from truckfinder import *
from chatterbot.parsing import datetime_parsing
import re
import csv
from logistics import *
from datetime import datetime,date
from lake import lake_question
from jobs import get_pso_response, dtf
#from waterline import waterline_question
from social import get_social_sentiment, get_posts
from sql_converter import * 
from math_adapter import *
from time import gmtime, strftime
from datetime import datetime,date
import ConfigParser
logging.basicConfig(filename='deanna_chatlog.log',level=logging.CRITICAL)

configParser = ConfigParser.RawConfigParser()   
configFilePath = r'config.txt'
configParser.read(configFilePath)

ip_address=str(configParser.get('server', 'ip_address'))
port_no=int(configParser.get('server', 'port_no'))


global data_loaded,corpus_len 

answered = ''
prev = ''
dt_chk = dtf('17-apr')

pso_calls = ["all_apps_list","which_app_failures","all_apps_list","which_app_failures","which_job_sla_threat","which_app_sla_threat","which_job_failures",
"sla_miss_apps_list","which_job_strt_late","which_job_end_late","which_job_mrk_cmpl","which_job_rstrt","chg_dt_to_today","sla_miss_utah","sla_miss_fdr",
"cnt_apps","cnt_apps_failures","cnt_apps_miss_sla","cnt_jobs","cnt_jobs_failures","cnt_jobs_restart","cnt_jobs_sla_threat","cnt_jobs_strt_late",
"cnt_jobs_end_late","cnt_jobs_mrk_cmpl"]
#print pso_calls[2]

trade_calls=["trade_check","balance_check"]
lake_calls = ["wires_fnames","cnt_wires_fnames","deposits_fnames","cnt_deposits_fnames","fdr_fnames",
"cnt_fdr_fnames","wires_accts","cnt_wires_accts","history_wires","history_deposits","history_fdr"]

#waterline_calls = ["ssn_suggested","ssn_accepted","bnkcd_suggested"]

social_calls = ["social_sentiment","social_posts"]

database_calls=["infosys","data","get","database_call","draw_graph","draw_table"]
xpo_cust_calls=["status","expect","not_reached"]
xpo_client_calls=["weight","truck"]
truck_calls=["search_truck","find_truck"]
math_calls=["math","plus","minus","power","multiplied","divided","+","-","*","/"]

payment = ['pending_amt','paidout_amt','confirm_balance','show_balance','confirm_issue','show_issue']

#global data_loaded,corpus_len 

# Initialize the number of parallel threads bot should run on. More cores allow for more parallel threads.
num_threads = 20

# Initialize the confidence threshold for answering questions
confidence_threshold = 0.68
# Get the length of the loaded corpus. Corpus load happens in the corpus.py program


app = bottle.app()

class EnableCors(object):
    name = 'enable_cors'
    api = 2

    def apply(self, fn, context):
        def _enable_cors(*args, **kwargs):
            # set CORS headers
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

            if bottle.request.method != 'OPTIONS':
                # actual request; reply with the actual response
                return fn(*args, **kwargs)

        return _enable_cors


def definition():
	global max_score
        global results
	global selected_answer
	global new_data_loaded
	global read_only
	global training
        global corpus_len 
	sentence_obama = ""
	max_score = 0.0
        results = []
	selected_answer = " "
	new_data_loaded = {}
	new_data_loaded['conversations'] = []
	read_only = 'N'
    	#corpus_len = 0
        #training  = 'N'
     

def t(x):
    	# This function is run in multi threaded mode. Each thread starts with the same global variables but does not share state.
	#print "Thread Run start ", (time.strftime("%H:%M:%S"))
        global max_score
        global results
	global selected_answer
        global corpus_len
	global num_threads
	k = x[0]
	# k is the question number in the corpus each thread is looping through.
	#print "k: ",k," num t: ",num_threads, " corpus_len: ",corpus_len
	input_question = x[1]
	for i in range(1,corpus_len+1):
	   if k < corpus_len:
		# corpus_question is the chosen kth question in the corpus
		corpus_question = data_loaded['conversations'][k][0]
		# score is a combination of levenshtein and WMD
            	score = levenshtein_distance(input_question,corpus_question)
		#score=10
		if score > max_score:
			max_score = score
                	#selected_answer = "hello"
			selected_answer = data_loaded['conversations'][k][1]
		k = k + num_threads
        return max_score,x[0],selected_answer


def run_parallel(ques):
    global num_threads
    #intialize a thread pool
    p = Pool(num_threads)
    l = []
    
    for x in range (1,num_threads + 1):
	#creating a a list thread no and incoming question   
	l.append((x,ques))
    #mapping the function and input to the thread pool
    results = p.map(t, l)
    p.close()
    p.join()
    #print results
    return results




def storeInformation(msg):
    global new_data_loaded
    global read_only
    if read_only ==  'N':
       if '~' in msg:
	  ques,ans = itemgetter(0,1)(msg.split('~'))
	  if ([ques,ans] not in new_data_loaded['conversations']): 
	        print "storing question and answer"
		new_data_loaded['conversations'].append([ques,ans]) 
		# Write YAML file
		with io.open('new_corpus_adds.yaml', 'w', encoding='utf8') as outfile:
    	    	   yaml.dump(new_data_loaded, outfile, default_flow_style=False, allow_unicode=True)
        	print new_data_loaded['conversations']
        	return "Ok. Question and Answer have been stored"
       else:
          return "Error: Please send API call in the format: question~answer"
    else:
       return "Bot is running in read only mode. Unable to accept edits."


def get_best_answer(possible_answers):
    #print max(possible_answers,key=itemgetter(0))[1]
    if (max(possible_answers,key=itemgetter(0))[0]) > confidence_threshold:	
	return str(max(possible_answers,key=itemgetter(0))[2]).split("||")[0]
    else:
	return "I'm sorry I do not understand. Could you please rephrase your question?"



if __name__ == '__main__':
    definition()
    global data_loaded
    global corpus_len
    #checking the the run parameters
    if len(sys.argv) > 1:
	print sys.argv[1],"option chosen"
        if sys.argv[1] == "read_only":
		read_only = 'Y'
        elif sys.argv[1] == "train":
            print "training the bot"
            training  = 'Y'
            data=train_bot()
	     #delete existing database
            drop_database()
	     #creating a fresh database
            create_database(data)
            data_loaded=fetch_all()
            #print data_loaded  
            corpus_len = len(data_loaded['conversations'])
            print "corpus length :", corpus_len
	
    else:
        #training == 'N'
        print "fetching from db"
        data_loaded=fetch_all()
        #print data_loaded  
        corpus_len = len(data_loaded['conversations'])
        print "corpus length :", corpus_len
            

    @app.route('/downloads/<filename:path>')
    def send_static(filename):
        return static_file(filename, root='static/',download=filename)

    @app.get('/')
    def getPing():
        return "Hey you have reached the mo-bot api"
    @app.get('/chat')
    def getResponse():
        print request
	msg = request.query.get('msg', '')

	msg=str(msg)
	print msg
	try:	   	
		question,racf_id,username,email=msg.split("||")

	except:
		question=msg
	   	username="a.Bot"
		racf_id="idbot00"
		email="wow@gmail.com"
	t = strftime("%Y-%m-%d %H:%M:%S", gmtime())
	#logging.critical('Time:%s' % t)
	#current_user_ip=request.environ.get('REMOTE_ADDR')
	#logging user details
	#logging.critical('Current User:%s' % username)
    	#logging.critical('Racf Id:%s' % racf_id)
    	#logging.critical('Email:%s' % email)
	start_time=strftime("%Y-%m-%d %H:%M:%S", gmtime())
	#logging.critical('Start Time:%s' % start_time)
	#logging.critical('Input Question:%s' % question)
	start = time.time()
        math_check=msg.split(" ")
        #math_match = [math_words for math_words in math_calls if any(word in math_words for word in math_check)]


	math_match=intersection(math_check,math_calls)
	print "math match",math_match
	print "length",len(math_match)
	if len(math_match)>0:
		response = get_calculated(question)
	        print "------",response, response.confidence
		if response.confidence > 0.80:
			response=str(response)
		
        	else:
			#running a multi threaded instance of comparisons 
			response=get_best_answer(run_parallel(question))
	else:
		#running a multi threaded instance of comparisons 
		response=get_best_answer(run_parallel(question))
	global prev 
        global dt_chk
        global answered

        # set prev to global value of previously successfully answered FRESH question
        if answered == 'Y':
	 	prev = prev


        #We have been able to answer an original question
        answered = 'Y'
                       
        # pso_calls is the list of pso adapter specific code words returned from the corpus as a response    
        if response in pso_calls:
               # Got a PSO Jobs related question
               input_query = question
               response, prev, dt_chk, answered = get_pso_response(input_query,response,prev,dt_chk,answered)
                
        elif response in lake_calls:
               # Got a Lake filesystem related question
               response = str(lake_question(response))
		
        #elif response in waterline_calls:
               #response = waterline_question(response)
               #waterline_question("ssn_suggested","ssn_accepted","bnkcd_suggested")
	
        elif response in social_calls:
               hashtags = {tag.strip("#") for tag in question.split() if tag.startswith("#")}
               print "hashtag:",hashtags
               if response == "social_sentiment":
                    response = get_social_sentiment(hashtags)
               elif response == "social_posts":
                    response = get_posts(hashtags)
        elif response in database_calls:
               print("sql")
	       print response
               query=ln_to_sql_convertor(question)
	       if response=='draw_table':
	            response=doQuery(query)
	       else:
		    response=query
	elif response in xpo_cust_calls:
                print "reached call"
		response=shipping_details(question,response)
		#print(shipping_details(question,response))
	#fork to the payout details function 
	elif response in xpo_client_calls:
		response=client_questions(question,response)
	elif response in truck_calls:
                response= find_truck(question,response)
	elif response in trade_calls:
		return trade(response,question)
        elif response=="stock_check":
                return fetch_stock(question,response)
	#elif response in payment:
		#response=get_details(racf_id.upper(),username,response)
            	#print "payment details: ",response
	#logging.critical('Answer:%s' %response)
	end_time=strftime("%Y-%m-%d %H:%M:%S", gmtime())
	#logging.critical('End Time:%s' % end_time)
	#logging.critical('Execution Time:%f' %(time.time()- start))
        print response 	
	return response
	#return str(run_parallel(msg))
    @app.get('/feedback')
    def logFeedback():
        meta_question = request.query.get('meta_question', '')
	print meta_question
	meta_question=str(meta_question)
	try:	   	
		meta_question,racf_id,username,email=meta_question.split("||")

	except:
		meta_question=meta_question
		print meta_question
	   	username="a.Bot"
		racf_id="id.bot00"
		email="a@gmail.com"
	t = strftime("%Y-%m-%d %H:%M:%S", gmtime())
    	logging.critical('Time:%s' % t)
	#logging user information 
	logging.critical('Current User:%s' % username)
    	logging.critical('Racf Id:%s' % racf_id)
    	logging.critical('Email:%s' % email)
	logging.critical('Meta Question Received:%s' % meta_question)
	return "Feedback recorded"
    @app.get('/store/<msg>')
    def storeInfo(msg):
	#adding a new question answer pair
	return storeInformation(msg)

app.install(EnableCors())

run(host=ip_address,port=port_no,reLoader=True,debug=True,server='tornado')


