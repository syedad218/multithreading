# -*- coding: utf-8 -*-

"""

Copyright: Infosys Ltd (2017)

Original code for the levenshtein algorithm : Gunther Cox 
@ https://github.com/gunthercox/ChatterBot/blob/master/chatterbot/comparisons.py

This module contains the text-comparison algorithm
designed to compare one statement to another. It is a combination of the levenshtein fuzzy compare
and the word vectors based WMD distance algorithm.

"""

import os
import re
import gensim
import logging
import ConfigParser
from gensim.models import Word2Vec
from nltk.corpus import stopwords

configParser = ConfigParser.RawConfigParser()   
configFilePath = r'config.txt'
configParser.read(configFilePath)

vector_path=str(configParser.get('paths', 'vector_path'))
#print vector_path
stop_words = stopwords.words('english')
infinity = float("inf")


#if not os.path.exists('/home/vaishnav/fastext/wiki.en.vec'):
    #raise ValueError("SKIP: You need to download the word vectors")
print "loading gensim stuff"

counter = 0

#model.init_sims(replace=True)
# Load word vectors into model using gensim 
model = gensim.models.KeyedVectors.load_word2vec_format('/home/vaishnav/fastext/wiki.en.vec', limit=10000)

#model = gensim.models.KeyedVectors.load_word2vec_format('~/glove/glove.6B.50d.word2vec.txt', binary=False)
# normalize word vectors
model.init_sims(replace=True)
#model_1.init_sims(replace=True)

def clean_sent(sent):
        
    '''
    Utility function to clean tweet text by removing links, special characters
    using simple regex statements.
    '''
    return ' '.join(re.sub("(@[A-Za-z0-9]+)|([^0-9A-Za-z \t])|(\w+:\/\/\S+)", " ", sent).split())


class Comparator:

    def __call__(self, statement_a, statement_b):
        return self.compare(statement_a, statement_b)

    def compare(self, statement_a, statement_b):
        return 0
    
    def get_initialization_functions(self):
        """
        Return all initialization methods for the comparison algorithm.
        Initialization methods must start with 'initialize_' and
        take no parameters.
        """
        initialization_methods = [
            (
                method,
                getattr(self, method),
            ) for method in dir(self) if method.startswith('initialize_')
        ]

        return {
            key: value for (key, value) in initialization_methods
        }
    
      
class LevenshteinDistance(Comparator):
    """
    Compare two statements based on the Levenshtein distance
    of each statement's text.

    For example, there is a 65% similarity between the statements
    "where is the post office?" and "looking for the post office"
    based on the Levenshtein distance algorithm.

    Also, compare the same 2 statements using the WMD algorithm: https://github.com/mkusner/wmd

     @inproceedings{kusner2015doc, 
     title={From Word Embeddings To Document Distances}, 
     author={Kusner, M. J. and Sun, Y. and Kolkin, N. I. and Weinberger, K. Q.}, 
     booktitle={ICML}, 
     year={2015}, 
     }  

     Finally, weight the levenshtein and WMD distances using custom weighting logic to bump up and down
     similarity scores to widen the gap between matching sets of statements and the rest of the statements.

     Note: The weights are derived separately using trial & error for our dataset. Please use cautiously and 
           tune them for your needs.

     """


    def compare(self, statement, other_statement):
        """
        Compare the two input statements.
        
        :return: The percent of similarity between the text of the statements.
        :rtype: float
        """
        import sys
        from nltk import word_tokenize
        from chatterbot import utils
        logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s')
        global counter
        #global model
        # Use python-Levenshtein if available
        try:
            from Levenshtein.StringMatcher import StringMatcher as SequenceMatcher
        except ImportError:
            from difflib import SequenceMatcher
        
        PYTHON = sys.version_info[0]
        
        # Return 0 if either statement has a falsy text value
        if not statement or not other_statement:
            return 0
        # Get the lowercase version of both strings
        if PYTHON < 3:
            statement_text = unicode(statement.lower())
            other_statement_text = unicode(other_statement.lower())
        else:
            statement_text = str(statement.text.lower())
            other_statement_text = str(other_statement.text.lower())
        
        similarity = SequenceMatcher(
            None,
            statement_text,
            other_statement_text
        )
        counter += 1
        #print "calculating similarity ****************************************************************************",counter 
        # Calculate a decimal percent of the similarity
        percent = int(round(100 * similarity.ratio())) / 100.0

        sentence_1 = clean_sent(statement_text).lower().split()
        sentence_2 = clean_sent(other_statement_text).lower().split()

        tokens1 = (sentence_1)
        tokens2 = (sentence_2)
        # Remove all stop words from the list of word tokens
        s1 = utils.remove_stopwords(tokens1, language='english')
        s2 = utils.remove_stopwords(tokens2, language='english')
        #s1 = [w for w in sentence_1 if w not in stop_words]
        #s2 = [w for w in sentence_2 if w not in stop_words]
        
        distance = model.wmdistance(s1, s2)
        distance_gensim = model.wmdistance(s1, s2)
        if distance == infinity:
            return percent
	
        elif percent > distance:
            if percent - distance < 0.25:
                #print other_statement_text, percent + 0.08, '%', '***DECENT MATCH****'
                #print 'percent: ', percent, 'distance: ', distance
                #print
                return percent + 0.08 + (0.15 * abs(1 - distance))
            else:
                #print other_statement_text, '*****CLOSE MATCH*****'
                #print 'percent: ', percent, 'distance: ', distance
                #print
                return percent + 1.0 + (0.15 * abs(1 - distance))
        elif percent > 0.4:
            if distance - percent < 0.15:
                #print other_statement_text, percent + 0.06, '%'
                #print 'percent: ', percent, 'distance: ', distance
                #print
                return percent + 0.06 + (0.15 * abs(1 - distance))
            else:
                #print other_statement_text, percent - 0.04, '%'
                #print 'percent: ', percent, 'distance: ', distance
                #print
                return (percent - 0.04) - (0.15 * abs(1 - distance))
	



# ---------------------------------------- #


levenshtein_distance = LevenshteinDistance()
