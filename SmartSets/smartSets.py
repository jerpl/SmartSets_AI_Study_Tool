#dependencies

#numpy
    #pip install numpy
#scipy
    #pip instll scipy
#scikitlearn
    #pip install -U scikit-learn
#spacy 
    # pip install -U spacy
    # python -m spacy download en_core_web_md
#textblob
    # pip install -U textblob
    # python -m textblob.download_corpora
#nltk
    #pip install -U nltk
    #nltk.download('wordnet') #lemmatizing tool 
    #nltk.download('stopwords') #common words that contribute little meaning to phrases 
    #nltk.download('punkt') #tokanize phrase into individual words

from pathlib import Path
import string
import random
import time
#imports and datasets for preprocessing
import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords

#for sentement analysis and spellcheck
from textblob import TextBlob

#imports for large dataset word vectors
import spacy

#imports for calculating word vectors manually if necessary
#from scipy import spatial
#from sklearn.feature_extraction.text import TfidfVectorizer
#from sklearn.feature_extraction.text import CountVectorizer

#local filesystem imports
import db

#globals
wordVectorizer = spacy.load("en_core_web_md") # word vectorizer model
SENTEMENT_FACTOR = 0.2 # the extent to which incorrect sentement will reduce your score
TIME_FACTOR = 0.01 # the extend to which taking a long time to answer will reduce your score
MAX_TIME_PENALTY = 0.5 # the most your score can be reduced for taking a long time
MIN_ATTEMPTS = 4 # the minimun number of times a card will be played before being hidden from a deck if it is mastered
INVALID_LIST = [None, "", " "] # list of invalid strings to check for when parsing term/defs
BASE_ANSWER_TIME = 5


def newSet(filepath):
    terms, definitions, status = preprocess(filepath)
    if (status == False):
        print("Error processing file: " + filepath + " please try again with a different file or fix format.")
        print("\nFormat in a text file is as follows: ")
        print("<questions>?<answer>\n<question>?<answer>\n<question>?<answer>\n...")
        return
    print("preprocessing complete")
    name = ''
    while name == '' or name == ' ':
        print("Enter a name for this study set. (Note: sets cannot be named 'q').")
        name = input(">> ")
    db.addSet(name, terms, definitions)


def studySession(setToStudy):
    cards = db.getCards(setToStudy)
    set_id = cards[0][0]

    initialAverage = round(sum(card[2] for card in cards)/len(cards),2)
    initialSumAttempts = db.getAttemptsSum(set_id)

    print(f"Your average mastery of this set is {initialAverage}")
    if cards[0][5]>0: #if the user has studied this set before, then allow them to chose sessionType and shuffle the deck
        print("\nPress enter to start a standard session, if you want to try a different session...")
        while True:
            print("Type r for refresher, e for extended, or i for info about session types")
            sessionType = input(">>")
            if sessionType == "i":
                sessionInfo()
            elif sessionType == '' or sessionType == 'r' or sessionType == 'e':
                cards = smartShuffle(cards, sessionType)
                break
            else:
                print("Invalid session type, try r, e, or i")

    print("\nFor each question, type your answer. If you give up, type: r! to reveal the answer (Warning: results in mastery of 0).\n")
    
    for i, card in enumerate(cards):
        if i == 0:
            input("Ready? Press enter to start!")
        else:
            input("\nPress enter for next question!")

        definitions = [] #the list which will contain the correct answer, and the user answer
        definitions.append(card[4]) #answer

        #time the user answer
        startTime = time.time()
        print(f"\n {card[3]}") #question
        userAnswer = input(">> ")
        print()
        endTime = time.time()
        elapsedTime = round(endTime-startTime, 2)

        if userAnswer == "r!":
            print(card[4]) #reveal correct answer but give you user a 0 in understanding
            masteryScore = 0
            print(f"Answer Revealed, given the score: 0")
        else:
            definitions.append(userAnswer) #a pair - (correct ans, user ans)

            # SWITCH TO COLE
            #process the answers for comparison
            simplifiedDefs, sentimentValues, answerLength = simplify(definitions)

            #vectorize and compute score with a number of factors
            sentenceVectors = vectorize(simplifiedDefs)
            # SWITCH TO JEREMY            
            attemptScore = round(compare(sentenceVectors, sentimentValues, elapsedTime, answerLength),2)

            print(f"\nThe correct answer was: '{definitions[0]}'")
            print(f"Your answer was given the score: {attemptScore}")
            masteryScore = db.getMastery(card[0],card[1])
            if masteryScore == 0.0:
                db.updateMastery(card[0], card[1], (attemptScore))
                continue
        #look into other ways to update mastery score
        db.updateMastery(card[0], card[1], ((attemptScore+masteryScore)/2))
        
    
    #compute new set avgMastery
    updatedCards = db.getCards(setToStudy)
    finalAverage = round(sum(card[2] for card in updatedCards)/len(updatedCards),2)
    #update new set avgMastery
    db.updateAvgMastery(cards[0][0], finalAverage)

    print(f"\nSession complete, your average mastery of this set has been updated from {initialAverage} to {finalAverage}")
    print(f"The total number of attempted cards of set has been updated from {initialSumAttempts} to {db.getAttemptsSum(set_id)}")


def sessionInfo():
    print("\n================================= Session Info =======================================")
    print("There are three session types you may choose from: Standard, Refresher, and Extended\n")
    print("- Standard: the default session type, plays all of your cards except the ones you've mastered, plays your cards with lower scores several more in a session")
    print("- Refresher: Ideal if you are already confident with a set but haven't studied it in a few days, plays all cards at random to refresh you. Even mastered cards")
    print("- Extended: Ideal for cramming or for keen learners, plays all cards an increased number of times, with fewer for mastered cards, and many more for cards with poor scores")
    print("======================================================================================\n")


def smartShuffle(cards, sessionType):
    if sessionType == 'r':
        random.shuffle(cards)
        print(f"Refresher session: your deck contains {len(cards)} cards")

    elif sessionType == '':
        extraAttempts = []
        cards.sort(key=lambda x:x[2])  #ask them all questions once in order of worst mastery score
        for card in cards: #additionally, add a card to the deck 2 extra times if it has a poor mastery score, and 1 extra time if it has an ok mastery
            if card[2]>=0.9 and card[5]>MIN_ATTEMPTS:
                cards.remove(card)
            elif card[2]<0.5:
                extraAttempts.extend([card]*2)
            elif card[2]<0.75:
                extraAttempts.append(card)
        random.shuffle(extraAttempts) #shuffle the extra cards
        cards.extend(extraAttempts)
        print(f"Standard session: your working deck contains {len(cards)} cards")
    
    elif sessionType == 'e':
        extraAttempts = []
        cardFrequency = {}
        for i, card in enumerate(cards): #greatly extend the deck based on mastery score
            if card[2]<0.25:
                extraAttempts.extend([card]*4)
                cardFrequency[i] = 5
            elif card[2]<0.5:
                extraAttempts.extend([card]*3)
                cardFrequency[i] = 4
            elif card[2]<0.75:
                extraAttempts.extend([card]*2)
                cardFrequency[i] = 3
            elif card[2]<0.9:
                extraAttempts.append(card)
                cardFrequency[i] = 2
            else:
                cardFrequency[i] = 1

        #cards.extend(extraAttempts)
        extendedCards = cards + extraAttempts
        random.shuffle(extendedCards)
        print(f"\nFor this study session of set_id:{card[0]}, your deck contains {len(extendedCards)} cards")
        print("The breakdown is as followes:\n")
        for i, card in enumerate(cards):
            print(f"Card {i}, with mastery {card[2]}, has been shuffled into the deck {cardFrequency[i]} times")
        return extendedCards


    

    return cards


def preprocess(filepath): # read in the document, and process into terms and definitions to be turned into a set
    terms = []
    definitions = []
    f = open(filepath, 'r')
    lines = f.readlines()
    status = True
    for line in lines:
        noNewLineChar = line.strip('\n') #get rid of \n from the end of the line
        splitLine = noNewLineChar.split('?')
        if (splitLine[0] not in INVALID_LIST):
            terms.append(splitLine[0])
        if (splitLine[1] not in INVALID_LIST):
            definitions.append(splitLine[1])
    if (len(terms) != len(definitions)):
        status = False
    return terms, definitions, status
    

def simplify(definitions): # perform several methods of simplifying a string to remove capitals, spelling errors, punctuation, etc
    lemmatizer = WordNetLemmatizer()
    stopWords = stopwords.words("english")
    simplifiedDefs = []
    sentimentValues = []
    answerLength = 0

    for i, line in enumerate(definitions):
        line = str.lower(line) #remove caps
        line = line.translate(str.maketrans('','',string.punctuation)) #remove punctuation

        #convert to textblob for spellcheck, and sentiment
        blobLine = TextBlob(line)
        correctedBlobLine = blobLine.correct() #spellcheck
        sentimentValues.append(correctedBlobLine.sentiment[0]) #[0] because it returns both polarity and subjectivity
        
        # tokanize(split into individual words) the now corrected line after turning it back into a string
        correctedString = str(correctedBlobLine)
        words = word_tokenize(correctedString)
        if (i == 0):
            answerLength = len(words)
        #remove stopwords
        lineWithoutStopWords = []
        for word in words:
            if word not in stopWords:
                lineWithoutStopWords.append(word)

        #lemmatize words - is slow and not strictly necessary, however, may improve accuracy, because it will help normalize several variations of a word into one vector which is good for our comparisons
        lemmatizedWords = []
        for word in lineWithoutStopWords: #lemmatize (reduce all nouns to simplest form --> dogs becomes dog), and then rejoin the line to a string
            lemmatizedWords.append(lemmatizer.lemmatize(word))
            reducedDefn = " ".join(lemmatizedWords)
        simplifiedDefs.append(reducedDefn)
        
    return simplifiedDefs, sentimentValues, answerLength


def vectorize(simplifiedDefs):
    vectorizedDefns = []
    for defn in simplifiedDefs:
        vectorizedDefn = wordVectorizer(defn)
        vectorizedDefns.append(vectorizedDefn)
    return vectorizedDefns


def compare(sentenceVectors, sentimentValues, elapsedTime, answerLength):
    #get average of the cosine similariy values for each word in the sentence
    cosineSimilarity = sentenceVectors[0].similarity(sentenceVectors[1]) 

    #improve accuracy by checking actual distance between sentement values
    if not ((sentimentValues[0]>=0 and sentimentValues[1]>=0) or (sentimentValues[0]<=0 and sentimentValues[1]<=0)):
        #sentements don't match, a serious problem, thus harsh penalties to score
        masteryScore = cosineSimilarity/(10*SENTEMENT_FACTOR)
    else:
        #sentements match but are not equal, minor reduction of score
        masteryScore = cosineSimilarity - SENTEMENT_FACTOR * abs(sentimentValues[0]-sentimentValues[1])

    #scale the mastery score based on how long the user took to answer
    timePenalty=0
    print(f"You took {elapsedTime} seconds to answer that question")
    # time threshold is 5 second + 1 second for every word in answer
    timeThreshold = BASE_ANSWER_TIME + answerLength
    if elapsedTime > timeThreshold:
         #after timeThreshold seconds, decrease score by 0.1 + (additional 0.01 per second - timeThreshold), until a max of half of the masteryscore
        timePenalty = min(TIME_FACTOR * (elapsedTime - timeThreshold), MAX_TIME_PENALTY * masteryScore)
        masteryScore -= timePenalty
        print(f"Becasue of time, your score was lowered from {masteryScore+timePenalty} to {masteryScore}")
    return masteryScore


def isValidFilepath(filepath):
    return Path.is_file(Path(filepath))


def main():
    #init
    reset = False
    db.init(reset)

    #application loop
    while True:
        print("\nWelcome to SmartSets, would you like to create a new set or study an existing set? Type n for new, s for study, sh to show sets, and q to quit.")
        action = input(">> ")
        if action == "q":
            break
        elif action == "n":
            prevNumSets = db.getNumSets()
            while (prevNumSets == db.getNumSets()):
                print("\nEnter the filepath of the txt file you wish to turn into a study set.")
                filepath = input(">> ")
                if (isValidFilepath(filepath)):
                    newSet(filepath)
                else:
                    print("The provided file could not be found, please verify the file exists and provide and absolute path if possible.")
        elif action == "s":
            if db.getNumSets() == 0:
                while (db.getNumSets() == 0):
                    print("Sorry you don't have any sets, enter a filepath of a txt file to create a study set before you can study.")
                    filepath = input(">> ")
                    if (isValidFilepath(filepath)):
                        newSet(filepath)
                    else:
                        print("The provided file could not be found, verify the file exists and provide and absolute path if possible.")
            else:
                setNames = db.getSetNames()
                print("Enter the name of the set you would like to study.")
                while True:
                    print(f"Here are all your sets {setNames}")
                    setToStudy = input(">> ")
                    if setToStudy in setNames:
                        studySession(setToStudy)
                        break
                    else:
                        print("Please chose a valid set name from the list of your sets.")
        elif action == "sh":
            print("\nExisting Set(s):\n")
            existingSets = db.getSetDisplay()
            print(f"Found {len(existingSets)} sets.")
            for i, set in enumerate(existingSets, 1):
                print(f"{i}. Name: {set[1]}, # Cards: {set[2]}, Set Average Mastery: {set[3]}, Attempts Sum: {db.getAttemptsSum(set[0])}")
            while True and len(existingSets) > 0:
                print("Type the name of a set you wish to see more info about or q to return to main menu.")
                setSelect = input(">> ")
                if setSelect == "q":
                    break
                elif (setSelect in db.getSetNames()):
                    cards = db.getCards(setSelect)
                    for i, card in enumerate(cards, 1):
                        print(f"\n{i}. Term: {card[3]}")
                        print(f"Definition: {card[4]}")
                        print(f"Attempts: {card[5]} Mastery: {card[2]}")
                    break              
        else:
            print("Invalid selection, try n, s, sh, or q")


if __name__ == "__main__":
    main()