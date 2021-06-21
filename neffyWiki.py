import requests
import requests_cache
import json
import re
import pprint
from tabulate import tabulate
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType

requests_cache.install_cache('wiki_cache', expire_after=60*60*24)

replace = {' ': '_', '(': '.28', ')': '.29', '/': '.2F', '?': '.3F'}

buttonCommand = 'wiki'
version = '3'

async def wikiButtonHandle(res, args):
    content, buttons = wikiHandle(args[0], args[1], args[2])
    if buttons:
        await res.respond(type=InteractionType.UpdateMessage, content=content, components=[buttons[i:i + 5] for i in range(0, len(buttons), 5)])
    else:
        await res.respond(type=InteractionType.UpdateMessage, content=content)

def setup(client):
    @client.command()
    async def wiki(ctx, *args):
        arg_list = list(args)
        page = arg_list.pop(0)
        heading = ' '.join(arg_list)
        content, buttons = wikiHandle(page, heading, 0)
        if buttons:
            await ctx.send(content, components=[buttons[i:i + 5] for i in range(0, len(buttons), 5)] )
        else:
            await ctx.send(content)
    
    @client.command()
    async def wikimove(ctx, *args):
        arg_list = list(args)
        page = arg_list[0]
        move = ' '.join(arg_list[1:])
        content = moveHandle(page, move)
        await ctx.send(content)
    return buttonCommand, {'version': version, 'buttonClickHandler': wikiButtonHandle}

def wikiHandle(page, heading='', pagination=0):
    if page.upper() in ['FILIA', 'CEREBELLA', 'PEACOCK', 'PARASOUL', 'MS._FORTUNE', 'PAINWHEEL', 'VALENTINE', 'DOUBLE', 'SQUIGLY', 'BIG_BAND', 'ELIZA', 'FUKUA', 'BEOWULF', 'ROBO-FORTUNE', 'ANNIE']:
        return 'I am intended for text pages, use !fd [character] [move] for move info', None
    contents = requests.get(f"https://wiki.gbl.gg/api.php?action=query&prop=revisions&titles=Skullgirls/{page}&rvslots=*&rvprop=content&formatversion=2&format=json").content
    contentjson = json.loads(contents)
    if 'missing' in contentjson['query']['pages'][0]:
        return f"Page Skullgirls/{page} not found (case sensitive)", None
    else:
        text = contentjson['query']['pages'][0]['revisions'][0]['slots']['main']['content']
        headings = headingList(text, page)

        hList = headingList(text, page)
        if type(heading) == str:
            if heading == '':
                location = []
            else:
                location = headingLocation(heading, hList)
                if location == False:
                    return f"Could not find heading {heading}", None
        else:
            location = heading
        element = hList

        title = 'Skullgirls/'+page
        back = [page]

        for index in location:
            element = element[2][index]
            title += ' -> '+element[0]
            back.append(element[0])
        back.pop()
        heading = element[0]
        content = element[1]
        content = sanitizeText(content)
        content = title + '\n' + content

        if len(content) > 2000:
            content = content[:1987] + '\n[Size limit]'

        buttons = []

        for index, button in enumerate(element[2]):
            loc = location.copy()
            loc.append(index)
            buttons.append(Button(style=ButtonStyle.blue, label=button[0], id=json.dumps(['wiki', '3', page, loc, 0])))
        loc = location.copy()
        while loc:
            loc.pop()
            buttons.append(Button(style=ButtonStyle.red, label="Back to " + back.pop(), id=json.dumps(['wiki', '3', page, loc, 0])))
        if(len(buttons) > 24):
            buttons = paginateButtons(buttons, int(pagination), page, location)
        for key, value in replace.items():
            heading = heading.replace(key, value)
        buttons.append(Button(style=ButtonStyle.URL, label=f'Link', url=f'https://wiki.gbl.gg/w/Skullgirls/{page}#{heading}'))

        return (content, buttons)

def headingList(text, page):
    #Replace the heading =s with unused chrs to make parsing it with regex actually possible
    #TODO: programatically find 4 characters that don't appear in the text rather than using 251-4, or some sort of htmlentities()-like escaping method to guarantee unused characters
    text = text.replace('=====', chr(254)).replace('====', chr(253)).replace('===', chr(252)).replace('==', chr(251))
    headingEscape = [chr(254), chr(253), chr(252), chr(251)]
    return findHeadings(text, page, headingEscape)

def findHeadings(text, heading, headingEscape):
    headingEscape = headingEscape.copy()                                #Copy to avoid mutating during recursion
    currentHeadingEscape = headingEscape.pop()

    #Get the text between the current heading and the next subheading, recursion and the next line stops it from grabbing past the next same-level heading

    headingContent = re.search(f'^[^{currentHeadingEscape}]*', text)[0]  
    
    #Get the title of each subheading and the text between it and the next subheading
    
    subHeadings = re.finditer(f'{currentHeadingEscape}([^{currentHeadingEscape}]*){currentHeadingEscape}([^{currentHeadingEscape}]*)', text)
    if subHeadings is not None:
        #Repeat for each match one subheading down
        return [heading, headingContent, [findHeadings(x.group(2), x.group(1), headingEscape) for x in subHeadings if x is not None]]

def headingLocation(heading, hList, location=[]):
    if hList[0] == heading:
        return location
    for index, headingList in enumerate(hList[2]):
        loc = location.copy()
        loc.append(index)
        recur = headingLocation(heading, headingList, loc)
        if recur:
            return recur
    return False

def paginateButtons(buttons, pagination, page, location):

    paged = []

    if pagination == 0:
        start = 0
    else:
        paged.append(Button(style=ButtonStyle.green,label='<',id=json.dumps(['wiki', '3', page, location, pagination-1])))
        start = 1 + 22*pagination
    paged.extend(buttons[start:])
    if len(paged) > 24:
        paged = paged[:23]
        paged.append(Button(style=ButtonStyle.green,label='>',id=json.dumps(['wiki', '3', page, location, pagination+1])))
    return paged


def sanitizeText(text):

    #Links
    text = re.sub(r'\[\[.*?\| ?(.*?)\]\]', r'\1', text)

    #Images and other shortcodes
    text = re.sub(r'\[\[[^\]]*\]\]', '', text)

    #Line Breaks
    text = re.sub(r'<br.*>', r'\n', text)

    #Button icons
    text = re.sub(r'{{NotationIcon-SG\|([A-z]{2})}}', r'\1', text)

    #Tables
    text = re.sub(r'{\|([^}]*)\|}', convertMediawikiTable, text, )

    #Bullet Points
    text = re.sub(r'\n(\*)(\**)', bulletPoints, text)

    #escape *s in a dumb way
    text = text.replace('*', chr(254))

    #Bold
    text = text.replace("'''", '**')
    text = re.sub(r'<(/)*b>', '**', text)

    #Deescape *s
    text = text.replace(chr(254), '\*')

    #Remove any tags we missed
    text = re.sub(r'<[^>]*>', '', text)

    #Remove any templates we missed
    text = re.sub(r'{{(.|\n)*}}', '', text)

    return text

def convertMediawikiTable(m):
    #It was at this point where he realised he knew he ~~fu~~ should have used an already made parser for mediawiki which for sure exists
    text = m.group(1)
    rawrows = text.split('\n|-')[1:]

    #handle *optional* table row
    if not rawrows[0].startswith(('\n|', '\n!')):
        rawrows.pop(0)

    rows = []
    for row in rawrows:
        rows.append(re.split(r'\n[\|\!]|\|\||\!\!', row)[1:])
    return '```\n'+tabulate(rows, tablefmt="grid")+'\n```'

def bulletPoints(m):
    return '\n'+'	'*len(m.group(2))+'•'

def moveHandle(page, move):
    contents = requests.get(f"https://wiki.gbl.gg/api.php?action=query&prop=revisions&titles=Skullgirls/{page}&rvslots=*&rvprop=content&formatversion=2&format=json").content
    contentjson = json.loads(contents)
    if 'missing' in contentjson['query']['pages'][0]:
        return f"Page Skullgirls/{page} not found (case sensitive)"
    else:
        text = contentjson['query']['pages'][0]['revisions'][0]['slots']['main']['content']

        #Sanitize move regex as it's user input
        move = re.sub(r'[#-.]|[\[-^]|[?|{}]', r'\\\g<0>', move)

        movematch = re.search(r'{{MoveData-SG[^{]*?name *= *'+move+f' *.*?}}\n[^\|]', text, re.DOTALL)
        if movematch is None:
            return f"Move {move} Not Found"
        moveData = movematch.group(0)
        moveData = moveData.split('{{AttackData-SG |')
        moveObject = []
        for data in moveData:
            version = {}
            fields = data.split('\n|')
            for field in fields:
                match = re.search(r'.*?([A-z0-9]*) *=(.*)', field)
                if match is not None:
                    key = match.group(1)
                    value = match.group(2)
                    version[key] = value
            moveObject.append(version)
            
        return json.dumps(moveObject)