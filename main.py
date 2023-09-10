import discord 
from discord.ext.tasks import loop
import dotenv
import os
import openai 
import schedule
import csv
import datetime
import time
dotenv.load_dotenv()

openai.api_key = os.getenv("OPENAI_TOKEN")
client = discord.Client(intents=discord.Intents.all())
contextLimit = 400
studBudDescription = "You are StudBud, a study buddy assistant who wants to help people stick with studying in the long term, specifically me, Jacob. Be nice, keep messages short, and be a friend to me."
discordUsername = os.getenv('DISCORD_USERNAME')

lastMsg = None
longTermMemory = ""
with open('memories/memory1.txt', 'w') as f:
    f.write("")

#Basic chat with gpt
def chat(text):
    conversation = [
        {"role": "system", "content": studBudDescription},
        {"role": "user", "content": text},
    ]

    response = openai.ChatCompletion.create(
        # model="gpt-3.5-turbo",
        model="gpt-4-0613",
        messages=conversation
    )

    message = response.choices[0].message.content
    return message



#On Start
@client.event
async def on_ready():
    checkToSeeIfStudBudShouldSendFirstMessage_ifSoThenSendIt.start()
    print("We have logged in as {0.user}".format(client))

maxMemoryLength = 600

#After message is received in server
@client.event 
async def on_message(msg, isStudBudTalkingFirst=False):
    global contextLimit, lastMsg
    lastMsg = msg
    

    with open('memories/memory1.txt', 'r') as f:
        longTermMemory = f.read()
        if len(longTermMemory) > maxMemoryLength:
            longTermMemory = longTermMemory[len(longTermMemory)-maxMemoryLength:len(longTermMemory)]
    if msg.author == client.user and not isStudBudTalkingFirst:
        return 
    
    #Clear the terminal (for debugging purposes)
    # os.system("cls")
    if msg.author.name == discordUsername and msg.content.startswith('$config'):
        message = msg.content.split()
        if len(message) != 2:
            return 
        else:
            if message[1].isnumeric():
                contextLimit = int(message[1])
            return
    if msg.author.name == discordUsername and msg.content.startswith('!clear'):
        return
    
    elif msg.author.name == discordUsername or isStudBudTalkingFirst:
        previousMessages = [message async for message in msg.channel.history()][::-1]
        messageToSendGPTPrecursor = ""
        
        messageToSendGPTPrecursor += "(Your long term memory): "
        if len(longTermMemory) != 0:
            messageToSendGPTPrecursor += longTermMemory
        else:
            messageToSendGPTPrecursor += '(none)'
        messageToSendGPTPrecursor += "\n\n"
        messageToSendGPTPrecursor += "Conversation (old to new) up to now:\n"
        
        messageToSendGPT = ""
        for i in range(len(previousMessages)-2, -1, -1):
            message = previousMessages[i]
            text = ""
            text += message.author.name + ": "
            text += message.content
            text += "\n\n"
            if len(text) + len(messageToSendGPT) > contextLimit:
                break
            messageToSendGPT = text + messageToSendGPT

        if isStudBudTalkingFirst:
             messageToSendGPT = messageToSendGPTPrecursor + messageToSendGPT + previousMessages[len(previousMessages)-1].author.name + ": " + previousMessages[len(previousMessages)-1].content + "\n\n" + "Note that you are sending a message first instead of responding to Jacob. Say something like what do you plan to study today (if it's morning) or if it's night you can ask what I did today or if its in the middle of the day, you can just check up on Jacob. The current time is: " + str(datetime.datetime.now())
        else:
            messageToSendGPT = messageToSendGPTPrecursor + messageToSendGPT + previousMessages[len(previousMessages)-1].author.name + ": " + previousMessages[len(previousMessages)-1].content + "\n\n" + "(To write to long term memory: Type '2', message to remember (keep it really short), and 'BREAK' and then the response to give to Jacob)"

        print(messageToSendGPT)
        msgToSendBack = chat(messageToSendGPT)



        print("\n\n" + msgToSendBack)
        if msgToSendBack[0] == '1':
            pass 
        elif msgToSendBack[0] == '2':
            toRemember = msgToSendBack.split('BREAK')[0][2:]
            with open('memories/memory1.txt', 'a') as f:
                f.write(toRemember) 
            with open('memories/allMemories.txt', 'a') as f: #Only used for logging
                f.write(toRemember)
            
            msgToSendBack = msgToSendBack.split('BREAK')[1]

        #Parse message into blocks of 2000 characters (discord limit)
        n = 2000
        msgArr = [msgToSendBack[i:i+n] for i in range(0, len(msgToSendBack), n)]
        for item in msgArr:
            await msg.channel.send(item)
    
#StudBud will send messages first at times. 
    #To check when to, check every minute to see if he should 
# @loop(count=None, seconds=1)
@discord.ext.tasks.loop(seconds=1)
async def checkToSeeIfStudBudShouldSendFirstMessage_ifSoThenSendIt():
    global lastMsg
    now = datetime.datetime.now()
    nowAsAString = now.strftime('%H:%M:%S')
    with open('data/timeToSendMessage.csv', 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            for item in row: 
                if nowAsAString == item:
                    await on_message(lastMsg, True)

@checkToSeeIfStudBudShouldSendFirstMessage_ifSoThenSendIt.before_loop
async def before_check_calendar():
    await client.wait_until_ready()  # Wait until bot is ready.

client.run(os.getenv('TOKEN'))