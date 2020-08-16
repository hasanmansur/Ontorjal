#! /usr/bin/python
from socket import *
import sys
import bitstring
import time
import random
#import pprint

# pretty printing
#pp = pprint.PrettyPrinter(indent=6)

# utilities functions
def hex_padding_4(a):
    return '{:04x}'.format(a)

def hex_padding_2(a):
    return '{:02x}'.format(a)

def get_random_id():
    pass

def get_header():
    header = {
        "id": hex_padding_4(random.randint(4000,10000)), #
        "flags": hex_padding_4(0b0000000100000000),
        "qdcount": hex_padding_4(1),
        "ancount": hex_padding_4(0),
        "nscount": hex_padding_4(0),
        "arcount": hex_padding_4(0)
    }
    #print('header\n', header)
    return header

# question
def get_qname(host_name):
    host_name_levels = host_name.split(".")
    qname = ''
    for level in host_name_levels:
        qname += hex_padding_2(len(level))
        for char in level:
            qname += hex_padding_2(ord(char))
    # terminating octet
    qname += hex_padding_2(0)
    return qname

def get_question(host_name):
    question = {
        "qname": get_qname(host_name),
        "qtype": hex_padding_4(1),
        "qclass": hex_padding_4(1)
    }
    #print('question\n', question)
    return question

# -- query
def get_query(header, question):
    print('Preparing DNS query..')
    query_bitstream = bitstring.pack('hex=id\
                    , hex=flags\
                    , hex=qdcount\
                    , hex=ancount\
                    , hex=nscount\
                    , hex=arcount\
                    , hex=qname\
                    , hex=qtype\
                    , hex=qclass'
                    , id=header['id']
                    , flags=header['flags']
                    , qdcount=header['qdcount']
                    , ancount=header['ancount']
                    , nscount=header['nscount']
                    , arcount=header['arcount']
                    , qname=question['qname']
                    , qtype=question['qtype']
                    , qclass=question['qclass']
                    )
    #print('query_bitstream\n', query_bitstream)
    return query_bitstream

def process_header(res_header_hexstring):
    id = res_header_hexstring[:4]
    flags = bin(int(res_header_hexstring[4:8], 16))[2:]
    qdcount = int(res_header_hexstring[8:12], 16)
    ancount = int(res_header_hexstring[12:16], 16)
    nscount = int(res_header_hexstring[16:20], 16)
    arcount = int(res_header_hexstring[20:24], 16)
    header = {
        'id': id,
        'flags': {
            'value': flags,
            'details': process_flags(flags)
        },
        'qdcount': qdcount,
        'ancount': ancount,
        'nscount': nscount,
        'arcount': arcount
        }
    #pp.pprint(header)
    return header

def process_flags(flags):
    QR = int(flags[:1], 16)
    OPCODE = int(flags[1:5], 16)
    AA = int(flags[5:6], 16)
    TC = int(flags[6:7], 16)
    RD = int(flags[7:8], 16)
    RA = int(flags[8:9], 16)
    Z = int(flags[9:12], 16)
    RCODE = int(flags[12:], 16)

    dict_flags = {
        'QR': {'val': QR, 'meaning': None},
        'OPCODE': {'val': OPCODE, 'meaning': 'Standard Query'},
        'AA': {'val': AA, 'meaning': None},
        'TC': {'val': TC, 'meaning': 'Truncation'},
        'RD': {'val': RD, 'meaning': 'Recursion Desired'},
        'RA': {'val': RA, 'meaning': None},
        'Z': {'val': Z, 'meaning': None},
        'RCODE': {'val': RCODE, 'meaning': None}
    }

    dict_flags['QR']['meaning'] = 'query' if dict_flags['QR']['val'] == 0 else 'response'
    dict_flags['AA']['meaning'] = 'authoritative server' if dict_flags['AA']['val'] == 1 else 'NOT authoritative server'
    dict_flags['RA']['meaning'] = 'Recursion Available' if dict_flags['RA']['val'] == 1 else 'Recursion NOT Available'

    if(dict_flags['RCODE']['val'] == 0): dict_flags['RCODE']['meaning'] = 'No error'
    elif(dict_flags['RCODE']['val'] == 1): dict_flags['RCODE']['meaning'] = 'Format error'
    elif(dict_flags['RCODE']['val'] == 2): dict_flags['RCODE']['meaning'] = 'Server failure'
    elif(dict_flags['RCODE']['val'] == 3): dict_flags['RCODE']['meaning'] = 'Name Error'
    elif(dict_flags['RCODE']['val'] == 4): dict_flags['RCODE']['meaning'] = 'Not Implemented'
    else: dict_flags['RCODE']['meaning'] = 'Refused'

    return dict_flags

def process_question(res_question_hexstring):
    QTYPE = res_question_hexstring[len(res_question_hexstring)-4:len(res_question_hexstring)]
    QCLASS = res_question_hexstring[len(res_question_hexstring)-8:len(res_question_hexstring)-4]
    QNAME_TERMINATING_OCTATE = res_question_hexstring[len(res_question_hexstring)-10:len(res_question_hexstring)-8]
    QNAME = res_question_hexstring[0:len(res_question_hexstring)-10]

    levels = []
    i = 0
    while i < len(QNAME):
        j = i+2
        len_octate = QNAME[i:j]
        len_level = (int(len_octate, 16)) * 2
        level_hex = QNAME[j:j+len_level]
        level = ''
        for elem in range(0, len(level_hex)-1, 2):
            level += chr(int(level_hex[elem:elem+2], 16))
        levels.append(level)
        i = j+len_level

    question = {
        'qname': '.'.join(levels),
        'qtype': {'val': int(QTYPE, 16), 'meaning': 'A'},
        'qclass': {'val': int(QCLASS, 16), 'meaning': 'IN'}
    }
    #pp.pprint(question)
    return question

def process_answer(res_answer_hexstring, host_name):
    # separating answer entries
    answer_entries = []
    for i in range(0, len(res_answer_hexstring), 32):
        #print(i)
        #print(res_answer_hexstring[i:i+32])
        answer_entry = res_answer_hexstring[i:i+32]
        answer_entries.append(answer_entry)
    #print(answer_entries)

    answers = []
    for i in range(len(answer_entries)):
        answers.append(process_answer_entry(answer_entries[i], host_name))
    return answers

def process_answer_entry(answer_entry, host_name):
    RDATA = answer_entry[len(answer_entry)-8:len(answer_entry)]
    RDLENGTH = answer_entry[len(answer_entry)-12:len(answer_entry)-8]
    TTL = answer_entry[len(answer_entry)-20:len(answer_entry)-12]
    CLASS = answer_entry[len(answer_entry)-24:len(answer_entry)-20]
    TYPE = answer_entry[len(answer_entry)-28:len(answer_entry)-24]
    NAME = answer_entry[len(answer_entry)-32:len(answer_entry)-28]
    IP_ADDR = resolve_IP(RDATA)

    answer = {
        'name': host_name,
        'type': {'val': int(TYPE, 16), 'meaning': 'A'},
        'class': {'val': int(CLASS, 16), 'meaning': 'IN'},
        'ttl': {'val':int(TTL, 16), 'meaning': 'seconds'},
        'rdlength': {'val':int(RDLENGTH, 16), 'meaning': 'rdata length in octets'},
        'rdata': {'val': IP_ADDR, 'meaning': 'resolved IP address'},
    }
    #print('-------------------------answer------------------------------------------')
    #pp.pprint(answer)
    return answer

def resolve_IP(RDATA):
    levels = []
    level = ''
    for elem in range(0, len(RDATA)-1, 2):
        levels.append(str(int(RDATA[elem:elem+2], 16)))
    #print(str(levels))
    return '.'.join(levels)

def process_authority(res_authority_hexstring, host_name):
    # separating autority entries
    autority_entries = []
    for i in range(0, len(res_authority_hexstring), 90):
        authority_entry = res_authority_hexstring[i:i+90]
        autority_entries.append(authority_entry)
    #print(autority_entries)

    authority = []
    for i in range(len(autority_entries)):
        authority.append(process_authority_entry(autority_entries[i], host_name))
    #print(authority)
    return authority

def process_authority_entry(authority_entry, host_name):
    NAME = host_name
    TYPE = authority_entry[4:8]
    CLASS = authority_entry[8:12]
    TTL = authority_entry[12:20]
    RDLENGTH = authority_entry[20:24]
    PRIMARY_NAME_SERVER = authority_entry[24:36]
    name_server_levels = hostname_from_level(PRIMARY_NAME_SERVER[:8])
    AUTHORITY_MAILBOX = authority_entry[36:50]
    mailbox_levels = hostname_from_level(AUTHORITY_MAILBOX[:10])
    SERIAL_NUMBER = authority_entry[50:58]
    REFRESH_INTERVAL = authority_entry[58:66]
    RETRY_INTERVAL = authority_entry[66:74]
    EXPIRE_LIMIT = authority_entry[74:82]
    MIN_TTL = authority_entry[82:90]

    authority_RR = {
        'name': host_name,
        'type': {'val': int(TYPE, 16), 'meaning': ''},
        'class': {'val': int(CLASS, 16), 'meaning': 'IN'},
        'ttl': {'val':int(TTL, 16), 'meaning': 'seconds'},
        'rdlength': {'val':int(RDLENGTH, 16), 'meaning': 'rdata length in octets'},
        'primary_name_server': {'val':'.'.join(name_server_levels) + '.' + host_name, 'meaning': ''},
        'authority_mailbox': {'val':'.'.join(mailbox_levels) + '.' + host_name, 'meaning': ''},
        'serial_number': {'val':int(SERIAL_NUMBER, 16), 'meaning': ''},
        'refresh_interval': {'val':int(REFRESH_INTERVAL, 16), 'meaning': 'hour'},
        'retry_interval': {'val':int(RETRY_INTERVAL, 16), 'meaning': 'hour'},
        'expire_limit': {'val':int(EXPIRE_LIMIT, 16), 'meaning': '7 days'},
        'min_ttl': {'val':int(MIN_TTL, 16), 'meaning': '3 hours'},
    }
    #print('-------------------------authority RR------------------------------------------')
    #pp.pprint(authority_RR)
    return authority_RR

def hostname_from_level(NAME_SERVER_OCTATE):
    levels = []
    i = 0
    while i < len(NAME_SERVER_OCTATE):
        j = i+2
        len_octate = NAME_SERVER_OCTATE[i:j]
        len_level = (int(len_octate, 16)) * 2
        level_hex = NAME_SERVER_OCTATE[j:j+len_level]
        level = ''
        for elem in range(0, len(level_hex)-1, 2):
            level += chr(int(level_hex[elem:elem+2], 16))
        levels.append(level)
        i = j+len_level
    #print(levels)
    return levels



def process_response(response_message, len_qname):
    # converet to bitstring
    response_bitstream = bitstring.BitArray(bytes=response_message)
    # convert to hexstring
    response_hexstring = response_bitstream.unpack('hex')[0]
    # header (in hexstring)
    res_header_hexstring = response_hexstring[:24]
    # non header (in hexstring)
    res_non_header_hexstring = response_hexstring[24:]
    # question (in hexstring)
    res_question_hexstring = res_non_header_hexstring[:8 + len_qname]
    # non question (in hexstring)
    res_non_question_hexstring = res_non_header_hexstring[len(res_question_hexstring):]

    # print() of various parts of response hexstring
    #print('response_hexstring:', response_hexstring)
    #print('res_header_hexstring:', res_header_hexstring)
    #print('res_non_header_hexstring:', res_non_header_hexstring)
    #print('res_question_hexstring', res_question_hexstring)
    #print('res_non_question_hexstring', res_non_question_hexstring)

    header = process_header(res_header_hexstring)
    question = process_question(res_question_hexstring)
    #print('len of res_non_question_hexstring', len(res_non_question_hexstring))

    # answer processing
    res_answer_hexstring = ''
    if(header['ancount'] != 0):
        #print('ancount', header['ancount'])
        answer_length = header['ancount'] * 32
        #print(answer_length)
        res_answer_hexstring = res_non_question_hexstring[:answer_length]

    answer = None
    if(len(res_answer_hexstring) > 0):
        #print('res_answer_hexstring', res_answer_hexstring)
        answer = process_answer(res_answer_hexstring, question['qname'])

    # authority processing
    res_authority_hexstring = ''
    if(header['nscount'] != 0):
        authority_length = header['nscount'] * 90
        #print(answer_length)
        res_authority_hexstring = res_non_question_hexstring[:authority_length]

    authority = None
    if(len(res_authority_hexstring) > 0):
        #print('res_authority_hexstring', res_authority_hexstring)
        authority = process_authority(res_authority_hexstring, question['qname'])

    # additional processing
    '''
    res_additional_hexstring = ''
    if(header['arcount'] != 0):
        res_additional_hexstring = res_non_question_hexstring[authority_length]

    additional = None
    '''

    # print section
    print('-------------------------header------------------------------------------')
    print('header.ID: ', header['id'])
    print('header.QR: ', header['flags']['details']['QR']['val'])
    print('header.OPCODE: ', header['flags']['details']['OPCODE']['val'])
    print('header.AA: ', header['flags']['details']['AA']['val'])
    print('header.TC: ', header['flags']['details']['TC']['val'])
    print('header.RD: ', header['flags']['details']['RD']['val'])
    print('header.RA: ', header['flags']['details']['RA']['val'])
    print('header.Z: ', header['flags']['details']['Z']['val'])
    print('header.RCODE: ', header['flags']['details']['RCODE']['val'])
    print('header.QDCOUNT: ', header['qdcount'])
    print('header.ANCOUNT: ', header['ancount'])
    print('header.NSCOUNT: ', header['nscount'])
    print('header.ARCOUNT: ', header['arcount'])

    print('-------------------------question------------------------------------------')
    print('question.QNAME: ', question['qname'])
    print('question.QTYPE: ', question['qtype']['val'], question['qtype']['meaning'])
    print('question.QCLASS: ', question['qclass']['val'], question['qclass']['meaning'])

    if(answer is not None):
        print('-------------------------answer------------------------------------------')
        for i in range(len(answer)):
            print('--answer', i+1, '--')
            print('answer.NAME: ', answer[i]['name'])
            print('answer.TYPE: ', answer[i]['type']['val'], answer[i]['type']['meaning'])
            print('answer.CLASS: ', answer[i]['class']['val'], answer[i]['class']['meaning'])
            print('answer.TTL: ', answer[i]['ttl']['val'])
            print('answer.RDLENGTH: ', answer[i]['rdlength']['val'])
            print('answer.RDATA: ', answer[i]['rdata']['val'])


    if(authority is not None):
        print('-------------------------authoritative section------------------------------------------')
        for i in range(len(authority)):
            print('--RR', i+1, '--')
            print('authority.NAME: ', authority[i]['name'])
            print('authority.TYPE: ', authority[i]['type']['val'])
            print('authority.CLASS: ', authority[i]['class']['val'], authority[i]['class']['meaning'])
            print('authority.TTL: ', authority[i]['ttl']['val'])
            print('authority.RDLENGTH: ', authority[i]['rdlength']['val'])
            print('authority.PRIMARY_NAME_SERVER: ', authority[i]['primary_name_server']['val'])
            print('authority.AUTHORITY_MAILBOX: ', authority[i]['authority_mailbox']['val'])
            print('authority.SERIAL_NUMBER: ', authority[i]['serial_number']['val'])
            print('authority.REFRESH_INTERVAL: ', authority[i]['refresh_interval']['val'])
            print('authority.RETRY_INTERVAL: ', authority[i]['retry_interval']['val'])
            print('authority.EXPIRE_LIMIT: ', authority[i]['expire_limit']['val'])
            print('authority.MIN_TTL: ', authority[i]['min_ttl']['val'])


#print(len(sys.argv))
#print((sys.argv[0]))
if len(sys.argv) <2:
    print('no host given')
elif len(sys.argv) > 2:
    print('more than 1 host given')
else:
    host_name = str(sys.argv[1])
    header = get_header()
    question = get_question(host_name)
    len_question = len(question['qname']) + len(question['qtype']) + len(question['qclass'])
    #print(len_question)
    query_bytestream = get_query(header, question).tobytes()
    #print('query_bytestream\n', query_bytestream)

    # server connection & sending
    server_name = "8.8.8.8"
    server_port = 53
    buffer_size = 1024
    print('Contacting DNS server..')
    client_socket = socket(AF_INET, SOCK_DGRAM)
    client_socket.settimeout(5)
    response_message = None
    server_address = None
    number_of_attempts = 3
    i = 1
    while i < 4:
        print('Sending DNS query..')
        try:
            client_socket.sendto(query_bytestream,(server_name, server_port))
            response_message, server_address = client_socket.recvfrom(buffer_size)
        except:
            i += 1
            continue
        if(response_message):
            break;
    client_socket.close()

    # response handling
    if(response_message is None):
        print('Hey there! I timed out! No aresponse :-(')
    else:
        print('DNS response received (attempt %d of 3)' %i)
        print('Processing DNS response..')
        #print('---------------------------------------------response--------------------------------------')
        #print('response from ' + server_address[0] + ':\n', response_message, server_address)
        process_response(response_message, len(question['qname']))
