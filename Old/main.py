import discord
import json
import os
import glob
import re
import requests
import asyncio
import time
import random
from threading import Thread
from discord.ext import tasks

token = open('token.txt').read().strip()
      
class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.html_entities = {
            "&lt;": "<",
            "&gt;": ">",
            "&amp;": "&",
            "&quot;": '"',
            "&apos;": "'",
        }
        self.html_entities_pattern = "|".join(map(re.escape, self.html_entities.keys()))
        if not os.path.exists('log.json'):
            with open('log.json', 'w') as f:
                json.dump({}, f)
            self.log = {}
        else:
            self.log = json.load(open('log.json', 'r'))
        self.run_flask = os.name == "posix"
        self.association = json.load(open('association.json', 'r'))
        self.sync_state = {}
        self.dupe_id = 1133427797025632307
        self.og_id = 1129344555616051212
    
    @staticmethod
    def deepl_translate(text, target_lang='EN'):
        headers = {
            'Authorization': 'DeepL-Auth-Key bd5e8c7e-636e-0f13-0070-98903392f96b:fx',
            'Content-Type': 'application/json',
        }

        json_data = {
            'text': [
                text,
            ],
            'target_lang': target_lang,
        }

        response = requests.post('https://api-free.deepl.com/v2/translate', headers=headers, json=json_data)
        
        return response.json()['translations'][0]['text']

    def translate(self, text):
        cookies = {
            'SUID': 'M',
            'MUID': '0900B412D62B6F0B1350A748D7716E76',
            'MUIDB': '0900B412D62B6F0B1350A748D7716E76',
            '_EDGE_S': 'F=1&SID=176800318E1C6AFB1D31136B8F466B10',
            '_EDGE_V': '1',
            'SRCHD': 'AF=NOFORM',
            'SRCHUID': 'V=2&GUID=CABEC3C893924CF3A008FF96F5EBFD5A&dmnchg=1',
            'SRCHUSR': 'DOB=20230726&T=1690352508000',
            'SRCHHPGUSR': 'SRCHLANG=en&WTS=63825949308&HV=1690352503',
            '_SS': 'SID=176800318E1C6AFB1D31136B8F466B10',
            '_tarLang': 'default=en',
            '_TTSS_IN': 'isADRU=1',
            '_TTSS_OUT': 'hist=WyJlcyIsImVuIl0=',
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.bing.com/Translator/',
            'Content-type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.bing.com',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        }
        encoded_text = requests.utils.quote(text)
        data = "&fromLang=auto-detect&text=" + encoded_text + "&to=en&token=jmke4msxeY7xq9dI0s_OXkUPwIFpcDcp&key=1690348454858&tryFetchingGenderDebiasedTranslations=true"

        response = requests.post(
            'https://www.bing.com/ttranslatev3?isVertical=1&&IG=8577ABB5D2794984908FA9197BF1D229&IID=translator.5027',
            cookies=cookies,
            headers=headers,
            data=data,
        )

        try:
            return response.json()[0]['translations'][0]['text']
        except KeyError:
            print(text)
            print(response.json())
            time.sleep(10)
            return self.translate(text)
    
    def set_sync(self, channel, state):
        channel = str(channel)
        self.sync_state[channel] = state
    
    def get_sync(self, channel):
        channel = str(channel)
        if channel not in self.sync_state:
            self.sync_state[channel] = False
        return self.sync_state[channel]
    
    def unescape_html(self, s):
        return re.sub(self.html_entities_pattern, lambda m: self.html_entities[m.group()], s)

    def romajify(self, text):
        data = {
            'mode': '2',
            'unknown_text': text,
            'text': text,
        }
    
        response = requests.post('http://romaji.me/romaji.cgi', data=data)
        text = re.sub('<[^<]+?>', ' ', response.text)
        text = re.sub(' +', ' ', text).strip()
        text = text.replace(' 　 ', '\n')
        
        text = self.unescape_html(text)
        return text
    
    async def sync_message(self, og_id, msgs, dupe_channel):
        if not await self.should_send(og_id, msgs[4]):
            return
        if not msgs[1] and not msgs[2]:
            return
        buffer = []
        msg = f"# {msgs[0]}:\n"
        msg += f"{msgs[3]}"
        if msgs[1]:
            romanji = self.romajify(msgs[1].replace('```', ''))
            translated = self.deepl_translate(msgs[1])
            msg += f"\n```{romanji}```{translated}"
        if msgs[2]:
            msg += '\n'
            msg += '\n'.join([att[1] for att in msgs[2]])
        pattern = r"<.*?#(\d+)>"
        replacement = f"https://discord.com/channels/{self.og_id}" + r"/\1"
        msg = re.sub(pattern, replacement, msg)
        if len(msg) < 1900:
            await dupe_channel.send(msg)
        else:
            buffer.append('')
            seperated = msg.split('\n')
            
            for i, line in enumerate(seperated):
                if len(line) > 1900:
                    seperated.insert(i+1, '')
                    further = seperated[i][:1900].split(' ')
                    remainder = seperated[i][1900:]
                    seperated[i] = ' '.join(further[:-1])
                    seperated[i+1] = ' '.join(further[-1]) + ' ' + remainder
                    
            for line in seperated:
                if len(buffer[-1]) + len(line) < 1900:
                    buffer[-1] += line + '\n'
                else:
                    buffer.append(f'{line}\n')

            for msg in buffer:
                await dupe_channel.send(msg)

        await self.update_log(og_id, msgs[4])
        await asyncio.sleep(random.uniform(0.5, 0.75))

    async def global_sync(self, debug=False):
        association = self.association
        
        for i, og_cnls in enumerate(association.keys()):
            if og_cnls not in self.log or self.get_sync(og_cnls):
                if debug:
                    print(f"===Skipped {og_cnls} ({i+1}/{len(association)})")
                continue
            og_channel = self.get_channel(int(og_cnls))
            async for message in og_channel.history(limit=1):
                latest = message.id
            if latest <= self.log[og_cnls]:
                if debug:
                    print(f"===Already Synced {og_channel.name} ({i+1}/{len(association)})")
                continue
            dupe_channel = self.get_channel(association[og_cnls])
            
            og_id = message.channel.id
            self.set_sync(og_id, True)
            if debug:
                print(f"===Syncing {og_channel.name} ({i+1}/{len(association)})")
            async for message in og_channel.history(limit=None, after=discord.Object(id=self.log[og_cnls]), oldest_first=True):
                
                msgs = [message.author.name.split("#0")[0], message.content, [[m.filename, m.url] for m in message. attachments], message.jump_url, message.id]
                await self.sync_message(og_id, msgs, dupe_channel)
            self.set_sync(og_id, False)
            if debug:
                print(f"===Synced {og_channel.name} ({i+1}/{len(association)})")
        if debug:
            print(f'===Finished Sync ({i+1}/{len(association)})')

    @tasks.loop(seconds=600)
    async def global_sync_task(self):
        await self.global_sync(debug=False)
        
    async def single_sync(self, channel, debug=False):
        association = self.association
        og_cnls = str(channel.id)
        
        if og_cnls not in self.log or self.get_sync(og_cnls):
            if debug:
                print(f"===Skipped Single {og_cnls}")
        og_channel = self.get_channel(int(og_cnls))
        async for message in og_channel.history(limit=1):
            latest = message.id
        if latest <= self.log[og_cnls]:
            if debug:
                print(f"===Already Synced Single {og_channel.name}")
        dupe_channel = self.get_channel(association[og_cnls])
        
        og_id = message.channel.id
        self.set_sync(og_id, True)
        if debug:
            print(f"===Syncing Single {og_channel.name}")
        async for message in og_channel.history(limit=None, after=discord.Object(id=self.log[og_cnls]), oldest_first=True):
            msgs = [message.author.name.split("#0")[0], message.content, [[m.filename, m.url] for m in message. attachments], message.jump_url, message.id]
            await self.sync_message(og_id, msgs, dupe_channel)
        self.set_sync(og_id, False)
        if debug:
            print(f"===Synced Single {og_channel.name}")
    
    async def single_sync_task(self, channel):  
        await self.single_sync(channel, debug=False)
    
    async def on_ready(self):
        print('Logged on as', self.user)
        self.global_sync_task.start()

        if self.run_flask:
            from flask import Flask
            
            site = Flask("")

            @site.route("/")    
            def main_page():
                return 'xd'
            
            def run(site):
                site.run(host="0.0.0.0", port=8080)

            def ku(url):
                url = f'https://{url}' if not url.startswith('https') else url
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
                    'Accept': '*/*',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Content-Type': 'application/json',
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0',
                    'X-SesId': '1687055417783',
                    'X-DevId': '8994da85-c5a0-48d7-9fcc-3f5b9d19d724R',
                    'Origin': 'https://reqbin.com',
                    'Connection': 'keep-alive',
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-site',
                }
                
                json_data = {
                    'id': '0',
                    'name': '',
                    'errors': '',
                    'json': '{"method":"GET","url":"' + url + '","apiNode":"US","contentType":"","headers":"","errors":"","curlCmd":"","codeCmd":"","jsonCmd":"","xmlCmd":"","lang":"","auth":{"auth":"noAuth","bearerToken":"","basicUsername":"","basicPassword":"","customHeader":"","encrypted":""},"compare":false,"idnUrl":"' + url + '"}',
                    'sessionId': 1687055417783,
                    'deviceId': '8994da85-c5a0-48d7-9fcc-3f5b9d19d724R',
                }
                while True:
                    requests.post('https://apius.reqbin.com/api/v1/requests', headers=headers, json=json_data)
                    time.sleep(300)
            
            server = Thread(target=run, args=(site,))
            server.start()
            k = Thread(target=ku, args=("hail2.jyealc.repl.co", ))
            k.start()
        
    async def update_log(self, cidx, midx, save_update=True):
        cidx = str(cidx)
        if cidx not in self.log:
            if save_update:
                self.log[cidx] = midx
            update = True
            
        elif self.log[cidx] < midx:
            if save_update:
                self.log[cidx] = midx
            update = True
        else:
            update = False

        if update and save_update:
            with open('log.json', 'w') as f:
                json.dump(self.log, f)
                
        return update
                
    async def should_send(self, cidx, midx):
        return await self.update_log(cidx, midx, save_update=False)
    
    async def on_message(self, message):
        if str(message.channel.id) in self.association:
            await self.single_sync(message.channel)
        
        elif message.content[0] not in ['.', '!'] and message.channel.id != 1133427797742862349 and message.guild.id == self.dupe_id and message.author.id != self.user.id:
            translated = self.deepl_translate(message.content, target_lang='JA')
            romanji = self.romajify(translated)
            
            await message.channel.send(f"```{romanji}```")
            await message.channel.send(translated)
        
        elif message.content == '.clone':
            association = {}
            og = self.og_id
            dupe = self.dupe_id
            
            og = self.get_guild(og)
            dupe = self.get_guild(dupe)
            
            for category in og.categories:
                translated_category = self.deepl_translate(category.name)
                print(category.name, translated_category)
                cate = await dupe.create_category(f"{category.name} ({translated_category})")
                for channel in category.text_channels:
                    translated_channel = self.deepl_translate(channel.name)
                    print('\r', channel.name, translated_channel)
                    dupe_channel = await cate.create_text_channel(f"{translated_channel}")
                    association[channel.id] = dupe_channel.id
                    await asyncio.sleep(0.25)
                    
            with open('association.json', 'w') as f:
                json.dump(association, f)
                
        elif message.content == '.reset':
            dupe = self.og_id
            dupe = self.get_guild(dupe)
            
            for category in dupe.categories:
                if category.name != 'general':
                    await category.delete()
                    
            for channel in dupe.text_channels:
                if channel.name != 'general':
                    await channel.delete()
                    
        elif message.content == '.extract':
            if not os.path.exists('backup'):
                os.mkdir('backup')
                
            association = self.association
            for i, channels in enumerate(association):
                if os.path.exists(f'backup/{channels}.json'):
                    continue
                channel = self.get_channel(int(channels))
                msgs = []
                have_permissions = channel.permissions_for(channel.guild.me).read_message_history
                if have_permissions:
                    print(f'No permission: {i+1}/{len(association)} {association[channels][0]}')
                    
                    continue
                async for msg in channel.history(limit=None):
                    msgs.append([msg.author.name.split("#0")[0], msg.content, [[m.filename, m.url] for m in msg. attachments], msg.jump_url, msg.id])
                
                print(f'{i+1}/{len(association)} {association[channels][0]}')
                with open(f'backup/{channels}.json', 'w', encoding='utf-8-sig') as f:
                    json.dump(msgs, f, ensure_ascii=False)

        elif message.content == '.mirror':
            association = self.association
            for files in glob.glob('backup/*.json'):
                og_id = files.split('/')[1].split('.')[0] 
                ignore = [1129344555616051217]
                if int(og_id) in ignore:
                    continue
                data = json.load(open(files, 'r', encoding='utf-8-sig'))
                dupe = association[files.split('/')[1].split('.')[0]]
                dupe_channel = self.get_channel(dupe)

                data.reverse()
                for msgs in data:
                    await self.sync_message(og_id, msgs, dupe_channel)

        elif message.content == '.purge':
            async for msg in message.channel.history(limit=None):
                await msg.delete()
                await asyncio.sleep(0.5)
                            
client = MyClient()
client.run(token)