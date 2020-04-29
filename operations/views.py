from django.shortcuts import render, get_object_or_404
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize, sent_tokenize
from blog.models import Post
import sys
from decimal import *
import codecs

# Create your views here.
def summary(request, id):

    # res=run([sys.executable,'//Users//sd873//Downloads//summarizer.py',obj.content],shell=False,stdout=PIPE)
    # print(res)

    def _generate_summary(sentences, sentenceValue, threshold):
        sentence_count = 0
        summary = ''

        for sentence in sentences:
            if sentence[:10] in sentenceValue and sentenceValue[sentence[:10]] > (threshold):
                summary += " " + sentence
                sentence_count += 1

        return summary

    def _score_sentences(sentences, freqTable) -> dict:
        sentenceValue = dict()

        for sentence in sentences:
            word_count_in_sentence = (len(word_tokenize(sentence)))
            for wordValue in freqTable:
                if wordValue in sentence.lower():
                    if sentence[:10] in sentenceValue:
                        sentenceValue[sentence[:10]] += freqTable[wordValue]
                    else:
                        sentenceValue[sentence[:10]] = freqTable[wordValue]

            sentenceValue[sentence[:10]] = sentenceValue[sentence[:10]] // word_count_in_sentence

        return sentenceValue

    def _create_frequency_table(text_string) -> dict:

        stopWords = set(stopwords.words("english"))
        words = word_tokenize(text_string)
        ps = PorterStemmer()

        freqTable = dict()
        for word in words:
            word = ps.stem(word)
            if word in stopWords:
                continue
            if word in freqTable:
                freqTable[word] += 1
            else:
                freqTable[word] = 1

        return freqTable

    def _find_average_score(sentenceValue) -> int:
        sumValues = 0
        for entry in sentenceValue:
            sumValues += sentenceValue[entry]

        # Average value of a sentence from original text
        average = int(sumValues / len(sentenceValue))

        return average


    # 1 Create the word frequency table
    # content="Football is the world’s most popular ball game in numbers of participants and spectators. Simple in its principal rules and essential equipment, the sport can be played almost anywhere, from official football playing fields (pitches) to gymnasiums, streets, school playgrounds, parks, or beaches. Football’s governing body, the Fédération Internationale de Football Association (FIFA), estimated that at the turn of the 21st century there were approximately 250 million football players and over 1.3 billion people “interested” in football; in 2010 a combined television audience of more than 26 billion watched football’s premier tournament, the quadrennial month-long World Cup finals."
    obj = get_object_or_404(Post, id=id)
    freq_table = _create_frequency_table(obj.content)
    # 2 Tokenize the sentences
    sentences = sent_tokenize(obj.content)
    # 3 Important Algorithm: score the sentences
    sentence_scores = _score_sentences(sentences, freq_table)
    # 4 Find the threshold
    threshold = _find_average_score(sentence_scores)
    # 5 Important Algorithm: Generate the summary
    summary = _generate_summary(sentences, sentence_scores, 1.4 * threshold)


    context={"object":obj,"result":summary}
    return render(request,'operations/summary.html',context)

def postag(request, id):


    tag_set = set()
    word_set = set()

    def parse_traindata():
        fin = "hmmmodel.txt"
        output_file = "hmmmoutput.txt"
        transition_prob = {}
        emission_prob = {}
        tag_list = []
        tag_count = {}

        try:
            input_file = codecs.open(fin, mode='r', encoding="utf-8")
            lines = input_file.readlines()
            flag = False
            for line in lines:
                line = line.strip('\n')
                if line != "Emission Model":
                    i = line[::-1]
                    key_insert = line[:-i.find(":") - 1]
                    value_insert = line.split(":")[-1]
                    if flag == False:
                        transition_prob[key_insert] = value_insert
                        if (key_insert.split("~tag~")[0] not in tag_list) and (key_insert.split("~tag~")[0] != "start"):
                            tag_list.append(key_insert.split("~tag~")[0])

                    else:
                        emission_prob[key_insert] = value_insert
                        key_tag = line[:-i.find(":") - 1]
                        val = key_tag.split("/")[-1]
                        j = key_insert[::-1]
                        word = key_insert[:-j.find("/") - 1]
                        # print word
                        word_set.add(word.lower())
                        if val in tag_count:
                            tag_count[val] += 1
                        else:
                            tag_count[val] = 1
                        tag_set.add(val)

                else:
                    flag = True
                    continue

            input_file.close()
            return tag_list, transition_prob, emission_prob, tag_count, word_set

        except IOError:
            fo = codecs.open(output_file, mode='w', encoding="utf-8")
            fo.write("File not found: {}".format(fin))
            fo.close()


    def viterbi_algorithm(sentence, tags, transition_prob, emission_prob, tag_count, word_set):
        # print "In Viterbi\n"
        global tag_set
        sentence = sentence.strip("\n")
        word_list = sentence.split(" ")
        current_prob = {}
        for tag in tags:
            tp = Decimal(0)
            em = Decimal(0)
            if "start~tag~" + tag in transition_prob:
                tp = Decimal(transition_prob["start~tag~" + tag])
            if word_list[0].lower() in word_set:
                if (word_list[0].lower() + "/" + tag) in emission_prob:
                    em = Decimal(emission_prob[word_list[0].lower() + "/" + tag])
                    current_prob[tag] = tp * em
            else:
                em = Decimal(1) / (tag_count[tag] + len(word_set))
                current_prob[tag] = tp

        if len(word_list) == 1:
            max_path = max(current_prob, key=current_prob.get)
            return max_path
        else:
            for i in range(1, len(word_list)):
                previous_prob = current_prob
                current_prob = {}
                locals()['dict{}'.format(i)] = {}
                previous_tag = ""
                for tag in tags:
                    if word_list[i].lower() in word_set:
                        if word_list[i].lower() + "/" + tag in emission_prob:
                            em = Decimal(emission_prob[word_list[i].lower() + "/" + tag])
                            max_prob, previous_state = max((Decimal(previous_prob[previous_tag]) * Decimal(
                                transition_prob[previous_tag + "~tag~" + tag]) * em, previous_tag) for previous_tag in
                                                           previous_prob)
                            current_prob[tag] = max_prob
                            locals()['dict{}'.format(i)][previous_state + "~" + tag] = max_prob
                            previous_tag = previous_state
                    else:
                        em = Decimal(1) / (tag_count[tag] + len(word_set))
                        max_prob, previous_state = max((Decimal(previous_prob[previous_tag]) * Decimal(
                            transition_prob[previous_tag + "~tag~" + tag]) * em, previous_tag) for previous_tag in
                                                       previous_prob)
                        current_prob[tag] = max_prob
                        locals()['dict{}'.format(i)][previous_state + "~" + tag] = max_prob
                        previous_tag = previous_state

                if i == len(word_list) - 1:
                    max_path = ""
                    last_tag = max(current_prob, key=current_prob.get)
                    max_path = max_path + last_tag + " " + previous_tag
                    for j in range(len(word_list) - 1, 0, -1):
                        for key in locals()['dict{}'.format(j)]:
                            data = key.split("~")
                            if data[-1] == previous_tag:
                                max_path = max_path + " " + data[0]
                                previous_tag = data[0]
                                break
                    result = max_path.split()
                    result.reverse()
                    return " ".join(result)

    obj = get_object_or_404(Post, id=id)

    tag_list, transition_model, emission_model, tag_count, word_set = parse_traindata()
    fin=codecs.open('hmminput.txt',mode='w',encoding="utf-8")
    fin=fin.write(obj.content)
    fin=codecs.open('hmminput.txt',mode='r',encoding="utf-8")
    fout = codecs.open("hmmoutput.txt", mode='w', encoding="utf-8")
    displayop = ""

    for sentence in fin.readlines():
        # print("New Sentence\n")
        path = viterbi_algorithm(sentence, tag_list, transition_model, emission_model, tag_count, word_set)
        sentence = sentence.strip("\n")
        word = sentence.split(" ")
        tag = path.split(" ")
        for j in range(0, len(word)):
            if j == len(word) - 1:
                fout.write(word[j] + "/" + tag[j] + u'\n')
                displayop = displayop + word[j] + "/" + tag[j] + u'\n'
            else:
                fout.write(word[j] + "/" + tag[j] + " ")
                displayop = displayop + word[j] + "/" + tag[j] + " "
    words=displayop.split(" ")
    arr=[]
    for word in words:
        keyval=word.split("/")
        arr.append([keyval[0],keyval[1]])



    context = {"object": obj,"result":arr}

    return render(request,'operations/tagging.html',context)