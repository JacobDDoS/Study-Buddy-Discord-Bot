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
studBudDescription = "You are StudBud, a study buddy assistant who wants to help people stick with studying in the long term, specifically me, Jacob. Be nice, keep messages short, and be a friend to me. Don't start responses with introductions like 'Hey Jacob!'"
discordUsername = os.getenv('DISCORD_USERNAME')

# model = "gpt-3.5-turbo"
model = "gpt-4-0613"
if model.startswith("gpt-3.5"):
    contextLimit = 8000
totalCost = 0
lastMsg = None
longTermMemory = ""
with open('memories/memory1.txt', 'w') as f:
    f.write("")

#Basic chat with gpt
def chat(text):
    global totalCost, model
    conversation = [
        {"role": "system", "content": studBudDescription},
        {"role": "user", "content": text},
    ]

    response = openai.ChatCompletion.create(
        # model="gpt-3.5-turbo",
        # model="gpt-4-0613",
        model = model,
        messages=conversation
    )

    message = response.choices[0].message.content
    cost = 0
    if model == "gpt-4-0613":
        cost = response.usage.completion_tokens * 0.06 / 1000 + response.usage.prompt_tokens * 0.03 / 1000
    elif model == "gpt-3.5-turbo":
        cost = response.usage.completion_tokens * 0.0015 / 1000 + response.usage.prompt_tokens * 0.002 / 1000
    totalCost += cost
    print("Cost of chat: " + str(cost) + ". Total Cost (during run time): " + str(totalCost))
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
    os.system("cls")
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
        for i in range(len(previousMessages)-1, -1, -1):
            message = previousMessages[i]
            text = ""
            text += message.author.name + ": "
            text += message.content
            text += "\n\n"
            if len(text) + len(messageToSendGPT) > contextLimit and i < len(previousMessages)-3:
                break
            messageToSendGPT = text + messageToSendGPT

        if isStudBudTalkingFirst:
             messageToSendGPT = messageToSendGPTPrecursor + messageToSendGPT + "Note that you are sending a message first instead of responding to Jacob. Say something like what do you plan to study today (if it's morning) or if it's night you can ask what I did today or if its in the middle of the day, you can just check up on Jacob. Note that I go to school on weekdays at 7:00, leave at 14:30, and get home and start studying at 2:50. The current time is: " + str(datetime.datetime.now())
        elif model.startswith("gpt-4"):
            messageToSendGPT = messageToSendGPTPrecursor + messageToSendGPT + "(To add to long term memory (only if it's important): Type '2', message to remember (keep it less than 50 characters), and 'BREAK' and then the response to give to Jacob)"
        elif model.startswith("gpt-3.5"):
            messageToSendGPT = messageToSendGPT

        print(messageToSendGPT)
        msgToSendBack = chat(messageToSendGPT)



        print("\n\n" + msgToSendBack)
        if msgToSendBack[0] == '1':
            pass 
        elif msgToSendBack[0] == '2' and model.startswith("gpt-4"):
            toRemember = msgToSendBack.split('BREAK')[0][2:]
            with open('memories/memory1.txt', 'a') as f:
                f.write(toRemember) 
            with open('memories/allMemories.txt', 'a') as f: #Only used for logging
                f.write(toRemember)
            
            msgToSendBack = msgToSendBack.split('BREAK')[1]

        if msgToSendBack.startswith("StudBud:"):
            msgToSendBack = msgToSendBack[9:]

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