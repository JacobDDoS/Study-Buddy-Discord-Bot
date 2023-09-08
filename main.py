import discord 
import dotenv
import os
import openai 
dotenv.load_dotenv()

openai.api_key = os.getenv("OPENAI_TOKEN")
client = discord.Client(intents=discord.Intents.all())
contextLimit = 4000
studBudDescription = "You are StudBud, a study buddy assistant who wants to help people stick with studying in the long term, specifically me, Jacob. Your goal is to be nice, kind, and encourage more studying! Don't ever ask how you can assist/help unless prompted to do so. Please refrain from summarizing when you don't have to, remember your goal is to act like a friend, a real life friend not just an AI. NEVER ASK HOW YOU CAN ASSIST OR HELP TODAY AND KEEP YOUR MESSAGES SHORT. Also, as StudBud you are not an AI, ACT HUMAN AND BE CASUAL. You don't have to start every response with a greeting. TALK LIKE IT IS A CASUAL CONVERSATION WITH A FRIEND AND YOU HAVE LOW TYPING SPEED."
discordUsername = os.getenv('DISCORD_USERNAME')

#Basic chat with gpt 3.5
def chat(text):
    conversation = [
        {"role": "system", "content": studBudDescription},
        {"role": "user", "content": text},
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=conversation
    )

    message = response.choices[0].message.content
    return message



#On Start
@client.event
async def on_ready():
    print("We have logged in as {0.user}".format(client))


#After message is received in server
@client.event 
async def on_message(msg):
    global contextLimit
    if msg.author == client.user:
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

    elif msg.author.name == discordUsername:
        previousMessages = [message async for message in msg.channel.history()][::-1]
        messageToSendGPTPrecursor = "Below are the previous messages for context (last messages first) (each message goes as the following, user: message and then separated by 3 new lines): \n\n\n"
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

        messageToSendGPT = messageToSendGPTPrecursor + messageToSendGPT + previousMessages[len(previousMessages)-1].author.name + ": " + previousMessages[len(previousMessages)-1].content

        print(messageToSendGPT)
        msgToSendBack = chat(messageToSendGPT)

        #Parse message into blocks of 2000 characters (discord limit)
        n = 2000
        msgArr = [msgToSendBack[i:i+n] for i in range(0, len(msgToSendBack), n)]
        for item in msgArr:
            await msg.channel.send(item)
    
client.run(os.getenv('TOKEN'))