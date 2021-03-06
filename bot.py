import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
import json
import requests
from datetime import datetime
from time import localtime, strftime
from google.transit import gtfs_realtime_pb2

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
KEY = os.getenv('MTA_API_KEY')

bot = commands.Bot(command_prefix='t/')

@bot.event
async def on_ready():
  try:
    print("Logged in as " + bot.user.name)
  except Exception:
    print(Exception)

@bot.command(
  help = "Get all the stations in a service line",
  brief = "Returns all the stations in a given line"
)
async def line(ctx, args):
  f = open('data\station_service_data.json')
  services = json.load(f)

  stations = []

  for line in services["service"]:
    if line["ident"] == args:
      for station in line["stationData"]:
        stations.append(station["stationName"])
      break

  stations = '\n'.join(stations)

  await ctx.channel.send(f"```{stations}```")

@bot.command(
  help = "Get next three train times in both directions",
  brief = "Returns next three train times in both directions"
)
async def time(ctx, *args):
  af = open('data/line_api.json')
  sf = open('data/station_service_data.json')
  apis = json.load(af)
  services = json.load(sf)
  
  api = ""
  station_code_N = ""
  next_arrivals_N = []
  terminal_N = ""
  station_code_S = ""
  next_arrivals_S = []
  terminal_S = ""
  
  user_line = args[0] # TODO: Type check between number and letter lines
  user_station = ' '.join(args[1:])

  # i think nested for loops are a big no no,
  # but they get the job done so ¯\_(ツ)_/¯
  # i am thinking of maybe doing switch statements but unsure
  for line in apis["service"]:
    if line["ident"] == user_line:
      api = line["api"]
      break

  for line in services["service"]:
    if line["ident"] == user_line:
      user_line = line["ident"] # just to be extra sure
      terminal_N = line["stationData"][0]["stationName"]
      terminal_S = line["stationData"][-1]["stationName"]
      for station in line["stationData"]:
        if station["stationName"] == user_station:
          station_code_N = station["stationCodeN"]
          station_code_S = station["stationCodeS"]
          break

  headers = {'x-api-key': f'{KEY}'}

  feed = gtfs_realtime_pb2.FeedMessage()
  resp = requests.get(api, headers=headers)
  feed.ParseFromString(resp.content)

  for trip in feed.entity:
    if trip.HasField('trip_update'):
      for stop in trip.trip_update.stop_time_update: # for some reason, i cannot access deeper than stop_time_update
        if stop.stop_id == station_code_N: # which is why i have to loop through the stops in each trip using two loops instead of looking at all stop codes in one loop
          if len(next_arrivals_N) < 3:
            next_arrivals_N.append(
              strftime("%I:%M:%S %p", localtime(stop.arrival.time))
            )
        elif stop.stop_id == station_code_S:
          if len(next_arrivals_S) < 3:
            next_arrivals_S.append(
              strftime("%I:%M:%S %p", localtime(stop.arrival.time))
            )
      if len(next_arrivals_N) == 3 and len(next_arrivals_S) == 3:
        break

  timeEmbed = discord.Embed(title = f'{station["stationName"]} ({user_line}) Arrival Times')
  timeEmbed.add_field(name=f'To {terminal_N}', value=f'[1] {next_arrivals_N[0]}', inline=True)
  timeEmbed.add_field(name='\u200b', value=f'[2] {next_arrivals_N[1]}', inline=True)
  timeEmbed.add_field(name='\u200b', value=f'[3] {next_arrivals_N[2]}', inline=True)
  timeEmbed.add_field(name=f'To {terminal_S}', value=f'[1] {next_arrivals_S[0]}', inline=True)
  timeEmbed.add_field(name='\u200b', value=f'[2] {next_arrivals_S[1]}', inline=True)
  timeEmbed.add_field(name='\u200b', value=f'[3] {next_arrivals_S[2]}', inline=True)
  timeEmbed.timestamp = datetime.utcnow()
  
  await ctx.channel.send(embed=timeEmbed)

bot.run(TOKEN)
