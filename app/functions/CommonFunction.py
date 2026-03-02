import json
import humps

from datetime import datetime

## utils
# import app.utils.WriteConsoleLog as __UTIL_WRITECONSOLELOG

# return datetime
def DATETIME():
  return datetime.now().isoformat(timespec = 'milliseconds').replace('T', ' ')

# return datetimeformat
def DATETIMEFORMAT(time):
  try:
    returnTime = datetime.strptime(time, '%Y-%m-%d %H:%M:%S.%f') if 'T' not in time else datetime.strptime(time.replace('T', ' '), '%Y-%m-%d %H:%M:%S.%f')
  except:
    try:
      returnTime = datetime.strptime(time, '%Y-%m-%d %H:%M:%S') if 'T' not in time else datetime.strptime(time.replace('T', ' '), '%Y-%m-%d %H:%M:%S')
    except:
      returnTime = ''

  return str(returnTime)

# return datetime milliseconds
def DATETIMEMILLIS():
  return str(round(datetime.now().timestamp() * 1000))

# return request (get method) format
def REQUESTGETFORMAT(json):
  tempStr = ''

  keyList = list(json.keys())

  for i in range(len(keyList)):
    tempStr = f'{tempStr}{keyList[i]}={json[keyList[i]]}'
    if i != len(keyList) - 1:
      tempStr = tempStr + '&'
  
  return tempStr

# return request (post method) format
def REQUESTPOSTFORMAT(json):
  tempJson = {
    'Data': {
      '0': []
    }
  }

  tempJson['Data']['0'] = [ json ]
  return tempJson

# return response format
def RESPONSEFORMAT(result, desc, payload):  
  return { 'Result': result, 'Desc': desc, 'Payload': payload }

# return flag that the dictionary does contain key
def CONTAINSKEY(jsonData, key):
  try:
    buf = jsonData[key]
  except:
    return False
  
  return True

# return trace string
def TRACESTR(errorStr):
  traceStr = ''

  try:
    for line in errorStr:
      if '~' not in line and '^' not in line:
        traceStr = traceStr + line.replace("'", '')
  except:
    traceStr = 'Error'

  return traceStr

# return parameters bind string
def BINDPARAM(query, params):
  result = query

  try:
    for i in range(len(params)):
      result = result.replace('?', f"'{params[i]}'" if str(type(params[i])) == "<class 'str'>" else params[i], 1)

  except:
    result = 'Error'
  
  return result

# return merged dictionary
def MERGEDICT(target, source):
  try:
    sourceKeys = source.keys()

    for key in sourceKeys:
      target[key] = source[key]
    
    return target
  except:
    return 'Error'

# return uppercase type key applied dictionary
def DICTKEYTOUPPER(data):
  try:
    if isinstance(data, dict):
      return { k.upper():DICTKEYTOUPPER(v) for k,v in data.items() }
    elif isinstance(data, list):
      return [ DICTKEYTOUPPER(v) for v in data ]
    else:
      return data
  except:
    return 'Error'

# return pascal type key applied dictionary  
def DICTKEYTOPASCAL(data):
  list = []

  try:
    idx = 0

    for item in data:
      dic = {}
      keys = item.keys()

      for key in keys:
        dic[f'{humps.pascalize(key.lower())}'] = data[idx][key]

      list.append(dic)

      idx = idx + 1

    return list
  except:
    return 'Error'

# return left padded string  
def LPAD(number, width, fillChar = '0'):
  return str(number).rjust(width, fillChar)

# return right padded string
def RPAD(number, width, fillChar = '0'):
  return str(number).ljust(width, fillChar)

# return json dump string
def JSONDUMPS(data):
  return json.dumps(data, ensure_ascii = False)

# return flag that check empty
def ISEMPTY(data):
  if data == None or data == '':
    return True
  else:
    return False

# return flag that check empty value
def ISEMPTYRETURNVALUE(data):
  if data == None or data == '':
    return ''
  else:
    return data
