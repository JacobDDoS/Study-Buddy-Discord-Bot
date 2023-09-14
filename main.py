import discord 
from discord.ext.tasks import loop
import dotenv
import os
import openai 
import schedule
import csv
import datetime
import json
dotenv.load_dotenv()

with open('config.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

openai.api_key = os.getenv("OPENAI_TOKEN")
client = discord.Client(intents=discord.Intents.all())
contextLimit = int(data['contextLimit'])
studBudDescription = "You are StudBud, a study buddy assistant who wants to help people stick with studying in the long term, specifically me, Jacob. Be nice, keep messages short, and be a friend to me. Don't start responses with introductions like 'Hey Jacob!'"
discordUsername = os.getenv('DISCORD_USERNAME')

model = data['model']
totalCost = 0
userContext = data['contextMessage']
longTermMemory = ""
with open('memories/memory1.txt', 'w', encoding='utf-8') as f:
    f.write("")

#Basic chat with gpt
def chat(text):
    global totalCost, model
    conversation = [
        {"role": "system", "content": studBudDescription},
        {"role": "user", "content": text},
    ]

    response = openai.ChatCompletion.create(
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


mainChannel = None

#On Start
@client.event
async def on_ready():
    global mainChannel
    mainChannel = client.get_channel(int(data['mainChannelId']))
    checkToSeeIfStudBudShouldSendFirstMessage_ifSoThenSendIt.start()
    print("We have logged in as {0.user}".format(client))

maxMemoryLength = int(data['memoryLimit'])
#After message is received in server
@client.event 
async def on_message(msg, isStudBudTalkingFirst=False):
    global contextLimit, model, userContext
    if not isStudBudTalkingFirst and msg.author == client.user:
        return 

    with open('memories/memory1.txt', 'r', encoding='utf-8') as f:
        longTermMemory = f.read()
        if len(longTermMemory) > maxMemoryLength:
            longTermMemory = longTermMemory[len(longTermMemory)-maxMemoryLength:len(longTermMemory)]
    
    
    #Clear the terminal (for debugging purposes)
    os.system("cls")
    if msg != None and msg.author.name == discordUsername and msg.content.startswith('$config'):
        message = msg.content.split()
        if len(message) != 2:
            return 
        else:
            if message[1].isnumeric():
                with open('config.json', 'w', encoding='utf-8') as f:
                    data['contextLimit'] = message[1]
                    contextLimit = int(message[1])
                    json.dump(data, f, indent=4)
            return
    if msg != None and msg.author.name == discordUsername and msg.content.startswith('$model'):
        message = msg.content.split()
        if len(message) != 2:
            return 
        else:
            model = message[1]
    if msg != None and msg.author.name == discordUsername and msg.content.startswith('!clear'):
        return
    if msg != None and msg.author.name == discordUsername and msg.content.startswith('$message'):
        message = msg.content.split("$message")
        if len(message) == 1:
            return 
        else:
            with open('config.json', 'w', encoding='utf-8') as f:
                data['contextMessage'] = message[1]
                userContext = message[1]
                json.dump(data, f, indent=4)
            userContext = message[1]
    
    elif isStudBudTalkingFirst or msg.author.name == discordUsername:
        previousMessages = [message async for message in mainChannel.history()][::-1]
        messageToSendGPTPrecursor = ""
        
        messageToSendGPTPrecursor += "(Your long term memory): "
        if len(longTermMemory) != 0:
            messageToSendGPTPrecursor += longTermMemory
        else:
            messageToSendGPTPrecursor += '(none)'
        messageToSendGPTPrecursor += "\n\n"
        
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

        if len(messageToSendGPT) == 0:
            messageToSendGPT = "(none)"

        if isStudBudTalkingFirst:
             messageToSendGPT = messageToSendGPTPrecursor + "\n" + userContext + "Conversation (old to new) up to now:\n" + "\n" + messageToSendGPT + "Note that you are sending a message first instead of responding to Jacob. Say something like what do you plan to study today (if it's morning) or if it's night you can ask what I did today or if its in the middle of the day, you can just check up on Jacob and see what he accomplished last block. Note that I go to school on weekdays at 7:00, leave at 14:30, and get home and start studying at 2:50. Include <@360592837622104065> in your response (to address/notify me). The current time is: " + str(datetime.datetime.now())
        elif model.startswith("gpt-4"):
            messageToSendGPT = messageToSendGPTPrecursor + "\n" + userContext + "Conversation (old to new) up to now:\n" + "\n" + messageToSendGPT + "(To add to long term memory (only if it's important): Type '2', message to remember (keep it less than 50 characters), and 'BREAK' and then the response to give to Jacob)"
        elif model.startswith("gpt-3.5"):
            messageToSendGPT = messageToSendGPT

        print(messageToSendGPT)
        with open('logs/promptAndResponse.txt', 'a', encoding='utf-8') as f:
            f.write("\n\n\n\n\nPrompt:\n" + messageToSendGPT)
        msgToSendBack = chat(messageToSendGPT)
        with open('logs/promptAndResponse.txt', 'a', encoding='utf-8') as f:
            f.write("\n\n\n\n\nResponse:\n" + msgToSendBack)



        print("\n\n" + msgToSendBack)
        if msgToSendBack[0] == '1':
            pass 
        elif msgToSendBack[0] == '2' and model.startswith("gpt-4"):
            toRemember = msgToSendBack.split('BREAK')[0][2:]
            with open('memories/memory1.txt', 'a', encoding='utf-8') as f:
                f.write(toRemember) 
            with open('memories/allMemories.txt', 'a', encoding='utf-8') as f: #Only used for logging
                f.write(toRemember)
            
            msgToSendBack = msgToSendBack.split('BREAK')[1]

        if msgToSendBack.startswith("StudBud:"):
            msgToSendBack = msgToSendBack[9:]

        #Parse message into blocks of 2000 characters (discord limit)
        n = 2000
        msgArr = [msgToSendBack[i:i+n] for i in range(0, len(msgToSendBack), n)]
        for item in msgArr:
            await mainChannel.send(item)
    
#StudBud will send messages first at times. 
    #To check when to, check every minute to see if he should 
@discord.ext.tasks.loop(seconds=1)
async def checkToSeeIfStudBudShouldSendFirstMessage_ifSoThenSendIt():
    now = datetime.datetime.now()
    nowAsAString = now.strftime('%H:%M:%S')
    with open('data/timeToSendMessage.csv', 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            for item in row: 
                if nowAsAString == item: 
                    await on_message(None, True)

@checkToSeeIfStudBudShouldSendFirstMessage_ifSoThenSendIt.before_loop
async def before_check_calendar():
    await client.wait_until_ready()  # Wait until bot is ready.

client.run(os.getenv('TOKEN'))