#!/usr/bin/python
import sys, os, re, argparse, hashlib

# Class handling the content of the lamedb.
class lamedb:
  def __init__(self, filename):
    self.filename = filename
    self.services = False
    self.transponders = False

    self.load()

    # Exit if there are no services or transponders.
    if len(self.services) == 0 or len(self.transponders) == 0:
      print "ERROR: No services or transponders available."
      sys.exit(-1)

  # Read lamedb file and load parsed content into memory.
  def load(self):
    # Access file and load content into memory.
    content = ""
    try:
      print "Reading file: " + self.filename
      f = open(self.filename)
      content = f.readlines()
      f.close()
    except:
      print "ERROR: Could not open or read from file: " + self.filename 
      sys.exit(-1)

    # Parse lamedb content.
    read_transponders = False
    read_services = False
    tmp = [] 
    self.transponders = {}
    self.services = {}

    print "Parsing content from file: " + self.filename
    for line in content:
      line = line.rstrip('\n')
      line = line.decode("ascii", "ignore")
      line = line.encode('utf-8')

      # Got END tag.
      if line == "end":
        read_transponders = False
        read_services = False
        continue 

      # Got START tag for: transponders.
      if line == "transponders":
        read_transponders = True
        continue 

      # Got START tag for: services.
      if line == "services":
        read_services = True
        continue

      # Read data for: transponders.
      # 1 - 00820000:1ce8:0071
      # 2 - s 12188000:27500000:1:4:130:2:0
      if read_transponders == True:
        if line == "/":
          self.transponders[tmp[0]] = tmp[1].replace("\t", "").replace(" ", ":")
          tmp = [] 
        else:
          tmp.append(line)

      # Read data for: services.
      # 1 - 1c85:00820000:1ce8:0071:1:0
      # 2 - Polsat Romans
      # 3 - p:Cyfrowy Polsat S.A.,C:0000
      if read_services == True:
        if line[0:2] == "p:":
          hsid, namespace, htsid, honid, stype, snumber = tmp[0].split(':')
          transponder = namespace + ":" + htsid + ":" + honid

          # Strip leading 0 from hex strings.
          hsid = re.sub("^0+","", hsid)
          namespace = re.sub("^0+","", namespace)
          htsid = re.sub("^0+","", htsid)
          honid = re.sub("^0+","", honid)
          stype = str(hex(int(stype))).lower()
          stype = stype[2:len(stype)]
          stype = re.sub("^0+","", stype)
          sref = "1:0:" + stype.upper() + ":" + hsid.upper() + ":" + htsid.upper() + \
            ":" + honid.upper() + ":" + namespace.upper() + ":0:0:0:" 

          self.services[sref] = {'hsid'        : hsid,        # Service id (SSID value from stream) in Hex.
                                 'namespace'   : namespace,   # DVB namespace in Hex.
                                 'htsid'       : htsid,       # Transport stream id in Hex.
                                 'honid'       : honid,       # Original network id in Hex.
                                 'stype'       : stype,       # Service type.
                                 'snumber'     : snumber,     # Service number in Decimal.
                                 'transponder' : transponder, # Transponder.
                                 'sname'       : tmp[1]}      # Service name.

          if sref == "1:0:19:6E:D:85:C00000:0:0:0:":
            print self.services[sref]

          # Split and parse provider data.
          provdata = []
          tmpprovdata = line.split(',')
          for tmpdata in tmpprovdata:
            psdata = tmpdata.split(':')
            if psdata[0] == "p":
              self.services[sref]['provider']= psdata[1]
            else:
              data = {}
              # Strip leading 0 of hex fields.
              psdata[1] = re.sub("^0+","", psdata[1])
              data[psdata[0]] = psdata[1]
              provdata.append(data)
          self.services[sref]['provider_data'] = provdata
          tmp = []
        else:
          tmp.append(line)

  # Get channelname and servicedata by using a service reference key.
  def getServiceBySRef(self, sref):
    try:
      return self.services[sref]
    except:
      return None

# Class handling the enigma2 bouquets and services.
class e2bouquets:
  def __init__(self, directory):
    self.directory = directory
    self.tv_bouquets = []
    self.tv_services = [] 
    self.radio_bouquets = []
    self.radio_services = []

    self.load()

  # Load the bouquet informations into memory.
  def load(self):
    if os.path.isfile(self.directory + "/" + "bouquets.tv"):
      print "Reading TV bouquets..."
      self.read_bqfile("bouquets.tv")
    if os.path.isfile(self.directory + "/" + "bouquets.radio"):
      print "Reading RADIO bouquets..."
      self.read_bqfile("bouquets.radio")

  # Read a bouquet file.
  def read_bqfile(self, filename):
    data = {}
    bqname = ""
    services = [] 
    subbouquets = [] 
    bqtype = ""

    try:
      f = open(self.directory + "/" + filename)
      bqs = f.readlines()
      f.close()
    except:
      print "ERROR: Could not open or read from file: " + self.directory + "/" + filename 
      sys.exit(-1)

    # Regex to match certain lines.
    bqname_re = re.compile('#NAME (.*) .*$')
    subbouquet_re = re.compile('.*BOUQUET "(.*)".*')
    service_re = re.compile('#SERVICE (.*:)')
    bqtype_re = re.compile('^#NAME .*\((.*)\)')

    for line in bqs:
      line = line.rstrip('\n')

      # Name.
      sresult = bqname_re.search(line)
      if sresult != None:
        bqname = sresult.group(1) 

      # Bouquet-Type.
      sresult = bqtype_re.search(line)
      if sresult != None:
        bqtype = sresult.group(1)

      # Subbouquet. 
      sresult = subbouquet_re.search(line)
      if sresult != None:
        subbouquets.append(sresult.group(1))
        continue

      # Service.
      sresult = service_re.search(line)
      if sresult != None:
        services.append(sresult.group(1))

    # Add bouquet to list if service exists.
    if len(services) > 0:
      if bqtype == "TV":
        self.tv_bouquets.append(bqname)
        for service in services:
          self.tv_services.append([service, bqname])
      if bqtype == "Radio":
        self.radio_bouquets.append(bqname)
        for service in services:
          self.radio_services.append([service, bqname])

    # Walk through other existing subbouquets.
    if len(subbouquets) > 0:
      for sub in subbouquets:
        self.read_bqfile(sub)

# Class handling the TV-Headend file structure.
class tvhstruct:
  def __init__(self, directory, lamedb, e2bq):
    self.directory = directory
    self.lamedb = lamedb 
    self.e2bq = e2bq
    self.services = {} 

    # Load existing TV-Headend configuration.
    self.load()

  # Load TV-Headend service configuration into memory.
  def load(self):
    tvh_svcname_re = re.compile('"svcname": "(.*)"')
    tvh_provider_re = re.compile('"provider": "(.*)"')
    tvh_sid_re = re.compile('"sid": (.*),')

    print "Reading TV-Headend service files..."
    for (path, dirs, files) in os.walk(self.directory + '/input/dvb/networks'):
      spath = path.split('/')

      if spath[len(spath)-1] == "services":
        for file in files:
          f = open(path + "/" + file)
          content = f.readlines()
          f.close()

          svcname = ""
          provider = ""
          sid = ""
          for line in content:
            line = line.rstrip('\n')
            sresult = tvh_svcname_re.search(line)
            if sresult != None:
              svcname = sresult.group(1)
            sresult = tvh_provider_re.search(line)
            if sresult != None:
              provider = sresult.group(1)
            sresult = tvh_sid_re.search(line)
            if sresult != None:
              sid = sresult.group(1)

          if svcname != "" and provider != "":
            self.services[file] = [svcname, provider]

  # Get a service from dictionary by using the name as key.
  def getServiceByName(self, svcname, provider):
    for key in self.services:
      if self.services[key][0] == svcname:
        return key
    return None

  # Write given bouquets into TV-Headend configuration.
  def writeBouquets(self):
    directory = self.directory + "/channeltags"
    print "Writing TV-Headend bouquet configuration..."

    # Loop through all bouquets and write configuration files.
    i = 1
    for bq in self.e2bq.tv_bouquets:
      self.writeBouquetFile(i, bq)
      i = i + 1
    for bq in self.e2bq.radio_bouquets:
      self.writeBouquetFile(i, bq)
      i = i + 1

  # Write a TV-Headend bouquet file.
  def writeBouquetFile(self, number, name):
    print "Wrting bouquet file: " + name
    directory = self.directory + "/channeltags"
    try:
      f = open(directory + "/" + str(number), 'w')
      f.write('{\n')
      f.write('\t"enabled": 1,\n')
      f.write('\t"internal": 0,\n')
      f.write('\t"titledIcon": 0,\n')
      f.write('\t"name": "' + name + '",\n')
      f.write('\t"comment": "",\n')
      f.write('\t"icon": "",\n')
      f.write('\t"id": ' + str(number) + '\n')
      f.write('}\n')
      f.close()
    except:
      print "ERROR: Could not write file: " + directory + "/" + str(number)
      sys.exit(-1)

  # Write into TV-Headend service configuration.
  def writeServices(self):
    directory = self.directory + "/channel"
    print "Writing TV-Headend service configuration..."

    i = 0
    # Write TV services.
    for service in self.e2bq.tv_services:
      i = i + 1
      print "Looking up service: " + str(service[0])
      servicedata = self.lamedb.getServiceBySRef(service[0])
      if servicedata == None:
        print "  ServiceReference from bouquet not found in lamedb: " + service[0]
        continue

      tvhkey = self.getServiceByName(servicedata['sname'], servicedata['provider'])
      if tvhkey == None:
        print "  Could not find service in TV-Headend service list: " + servicedata['sname'] + " (" + \
          servicedata['provider'] + ")"
        continue

      bqn = 1
      for bq in self.e2bq.tv_bouquets:
        if bq == service[1]:
          break;
        bqn = bqn + 1 
      self.writeServiceFile(servicedata['hsid'], i, tvhkey, bqn)

    # Write RADIO services.
    for service in self.e2bq.radio_services:
      i = i + 1
      servicedata = self.lamedb.getServiceBySRef(service[0])
      if servicedata == None:
        print "ERROR: ServiceReference from bouquet not found in lamedb: " + service[0]
        continue

      tvhkey = self.getServiceByName(servicedata['sname'], servicedata['provider'])
      if tvhkey == None:
        print "  Could not find service in TV-Headend service list: " + servicedata['sname'] + " (" + \
          servicedata['provider'] + ")"
        continue

      bqn = len(self.e2bq.tv_bouquets)+1
      for bq in self.e2bq.radio_bouquets:
        if bq == service[1]:
          break;
        bqn = bqn + 1
      self.writeServiceFile(servicedata['hsid'], i, tvhkey, bqn)

  # Write a TV-Headend service file.
  def writeServiceFile(self, sid, channelnumber, tvhkey, tag):
    directory = self.directory + "/channel"
    try:
      m = hashlib.md5()
      m.update(sid)
      md5sid = m.hexdigest()
      f = open(directory + "/" + str(md5sid), 'w')
      f.write('{\n')
      f.write('\t"number": ' + str(channelnumber) + ',\n')
      f.write('\t"dvr_pre_time": 5,\n')
      f.write('\t"dvr_pst_time": 5,\n')
      f.write('\t"services": [\n')
      f.write('\t\t"' + tvhkey + '"\n')
      f.write('\t],\n')
      f.write('\t"tags": [\n')
      f.write('\t\t' + str(tag) + '\n')
      f.write('\t]\n')
      f.write('}\n')
      f.close()
    except:
      print "ERROR: Could not write file: " + directory + "/" + str(md5sid)
      sys.exit(-1)

# Main entry for this script.
def main(argv):
  inputdir = ""
  outputdir = ""

  parser = argparse.ArgumentParser(description = 'Enigma2 to TV-Headend channel and bouquet converter')
  parser.add_argument('-i','--input', help = 'Enigma2 input directory', required = True)
  parser.add_argument('-o','--output', help = 'TV-Headend configuration directory', required = True)
  args = parser.parse_args()

  inputdir = args.input.rstrip('/')
  outputdir = args.output.rstrip('/')

  # Check whether directories exist.
  if not os.path.isdir(args.input):
    print "ERROR: Enigma2 source directory does not exist"
    sys.exit(-1)
  if not os.path.isdir(args.output):
    print "ERROR: TV-Headend destination directory does not exist"
    sys.exit(-1)

  # Check directory for channeltags.
  directory = outputdir + "/channeltags"
  print "Writing TV-Headend bouquet configuration..."
  if not os.path.isdir(directory):
    try:
      os.makedirs(directory)
    except:
      print "ERROR: Could not create directory: " + directory
      sys.exit(-1)
  else:
    print "ERROR: Directory already exists: " + directory
    sys.exit(-1)

  # Check directory for channel services.
  directory = outputdir + "/channel"
  print "Writing TV-Headend service configuration..."
  if not os.path.isdir(directory):
    try:
      os.makedirs(directory)
    except:
      print "ERROR: Could not create directory: " + directory
      sys.exit(-1)
  else:
    print "ERROR: Directory already exists: " + directory
    sys.exit(-1)

  # Trigger main functions.
  ldb = lamedb(inputdir + '/lamedb')
  e2bq = e2bouquets(inputdir)
  tvh = tvhstruct(outputdir, ldb, e2bq)
  tvh.writeBouquets()
  tvh.writeServices()

# Main entry for script.
if __name__ == "__main__":
  main(sys.argv[1:])


