# bot.py
import os
import pymongo
import requests
import json
import discord
from dotenv import load_dotenv
intents = discord.Intents.default()
intents.members = True
intents.messages = True

load_dotenv() 
client = discord.Client(intents=intents)

TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('SERVER')
db_url = os.getenv('DB_URL')
mongoClient = pymongo.MongoClient(db_url)

def get_new_member(member):
    return {"_id" : member.id,
            "name" : member.name,
            "stocks" : []}

def get_stock_info(url, headers, querystring):
    try:
        response = requests.get(url, headers=headers, params=querystring)
        return response.json()
    except Exception:
        return None

def getQuotes(code, time):
    url = "https://twelve-data1.p.rapidapi.com/quote"
    timeFrame = time
    querystring = {"symbol":code, "interval":"1" + timeFrame, "format":"json", "outputsize":"1"}
    headers = {
        'x-rapidapi-key': "76ddaf3224mshda367e947dd4415p1c17f7jsn86cb83e7e8cb",
        'x-rapidapi-host': "twelve-data1.p.rapidapi.com"
    }
    return get_stock_info(url, headers, querystring)
    
def getPrice(code):
    url = "https://twelve-data1.p.rapidapi.com/price"
    querystring = {"symbol":code, "outputsize":"1", "format":"json"}
    headers = {
        'x-rapidapi-key': "76ddaf3224mshda367e947dd4415p1c17f7jsn86cb83e7e8cb",
        'x-rapidapi-host': "twelve-data1.p.rapidapi.com"
    }
    return get_stock_info(url, headers, querystring)

@client.event
async def on_member_join(member):
    new_member = get_new_member(member)
    mongoClient.DiscordBotDB.Members.insert_one(new_member)
    try:
        await member.send('Welcome to the Berver ' + member.name)
    except Exception:
        pass

@client.event
async def on_member_remove(member):
    mongoClient.DiscordBotDB.Members.delete_one({"_id": member.id})
    try:
        await member.send('Sad to see you leave. We hope to see you again: ' + member.name)
    except Exception:
        pass

@client.event
async def on_ready():
    for guild in client.guilds:
        if guild.name == GUILD:
            break

    print(
        f'{client.user} is connected to the following guild:\n'
        f'{guild.name}(id: {guild.id})'
    )
    
    members = '\n - '.join([member.name for member in guild.members if not member.bot])
    print(f'Guild Members:\n - {members}')

    for member in guild.members:
        if not (mongoClient.DiscordBotDB.Members.find_one({"_id": member.id}) or member.bot):
            new_member = get_new_member(member)
            mongoClient.DiscordBotDB.Members.insert_one(new_member)

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.content.startswith('$stock'):
        req = message.content.split()
        if (len(req) < 2):
            await message.channel.send('all requests must have at least one parameter')
            return
        infoType = req[1]
        stock = req[2].upper()

        if (infoType == 'price'):
            price = getPrice(stock)
            if (price == None):
                await message.channel.send("Could not get price for " + stock)
            else:
                await message.channel.send(stock + " current price : " + price["price"])

        elif (infoType == 'data'):
            if (len(req) != 4):
                await message.channel.send("Stock data requests must contain a third: timeframe parameter")
                return
            time = req[3].lower()
            if (time == "day" or time == "month" or time == "week"):
                quote = getQuotes(stock, time)
                if (quote == None):
                    await message.channel.send("Could not get data for " + stock)
                else:
                    await message.channel.send("Stock: " + quote["name"] + " (" + stock + ") " + "\n"
                                            "High: " + quote["high"] + "\n" +
                                            "Low: " + quote["low"] + "\n" + 
                                            "Volume: " + quote["volume"])
                return
            await message.channel.send("timeframe parameter must be: date, week, month or year")

        elif (infoType == 'info'):
            quote = getQuotes(stock,'day')
            if (quote == None):
                await message.channel.send("Could not get info for " + stock)
            else:
                await message.channel.send("Company: " + quote["name"] + "\n" + 
                                           "Exchange: " + quote["exchange"] + "\n" + 
                                           "Currency traded in: " + quote["currency"])
        elif (infoType == 'add'):
            stock_list = mongoClient.DiscordBotDB.Members.find_one({"_id": message.author.id})["stocks"]
            if stock in stock_list:
                await message.channel.send("You already have " + stock + " in you list of saved stocks")
                return
            price = getPrice(stock)
            if (price == None):
                await message.channel.send("Could not add stock " + stock)
            else:
                stock_list.append(stock)
                print(stock_list)
                mongoClient.DiscordBotDB.Members.find_one_and_update({"_id": message.author.id}, {'$set': {'stocks': stock_list}})

        elif (infoType == 'remove'):
            stock_list = mongoClient.DiscordBotDB.Members.find_one({"_id": message.author.id})["stocks"]
            if not (stock in stock_list):
                await message.channel.send(stock + " is not in you saved list of stocks")
            else:
                stock_list.remove(stock)
                print(stock_list)
                mongoClient.DiscordBotDB.Members.find_one_and_update({"_id": message.author.id}, {'$set': {'stocks': stock_list}})
        
        elif (infoType == 'my_stocks'):
            stock_list = mongoClient.DiscordBotDB.Members.find_one({"_id": message.author.id})["stocks"]
            print(stock_list)
            if not (stock in stock_list):
                await message.channel.send(stock + " is not in you saved list of stocks")
            else:
                stock_list.remove(stock)
                print(stock_list)
                mongoClient.DiscordBotDB.Members.find_one_and_update({"_id": message.author.id}, {'$set': {'stocks': stock_list}})

        else:
            await message.channel.send(infoType + 'is not a valid command')

client.run(TOKEN)