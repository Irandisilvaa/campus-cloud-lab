"""Gera templates legíveis e incorpora a aplicação no UserData, sem downloads na EC2."""
import base64
import gzip
import io
from pathlib import Path
import tarfile
import yaml

def represent_string(dumper, value):
    return dumper.represent_scalar('tag:yaml.org,2002:str', value, style='|' if '\n' in value else None)
yaml.SafeDumper.add_representer(str, represent_string)

ROOT = Path(__file__).resolve().parents[1]
def ref(name): return {'Ref': name}
def attr(name, field): return {'Fn::GetAtt': [name, field]}
def sub(text): return {'Fn::Sub': text}
def resource(kind, properties, **extra): return {'Type': 'AWS::' + kind, 'Properties': properties, **extra}
def template(description, params, resources, outputs, **extra):
    return {'AWSTemplateFormatVersion': '2010-09-09', 'Description': description, 'Parameters': params, **extra, 'Resources': resources, 'Outputs': {k: {'Value': v} for k,v in outputs.items()}}
def param(description, **extra): return {'Type': 'String', 'Description': description, **extra}
def write(name, data):
    (ROOT / 'infra' / name).write_text('# Gerado por scripts/build_templates.py. Fontes da aplicação em app/.\n' + yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=110), encoding='utf-8')

buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode='w') as tar:
    for path in sorted((ROOT / 'app').glob('*')):
        if not path.is_file(): continue
        raw = path.read_bytes()
        entry = tarfile.TarInfo(path.name); entry.size = len(raw); entry.mode = 0o644; entry.mtime = 0
        tar.addfile(entry, io.BytesIO(raw))
encoded = base64.b64encode(gzip.compress(buf.getvalue(), mtime=0)).decode()
def user_data(node):
    script = '''#!/bin/bash
set -euo pipefail
exec > >(tee /var/log/campus-bootstrap.log /dev/console) 2>&1
command -v python3
mkdir -p /opt/campus
base64 -d <<'CAMPUS_ARCHIVE' | tar -xz -C /opt/campus
''' + encoded + '''
CAMPUS_ARCHIVE
chmod -R a+rX /opt/campus
cat > /etc/systemd/system/campus.service <<'SERVICE'
[Unit]
Description=Campus Cloud Lab
After=network-online.target
Wants=network-online.target
[Service]
User=nobody
Group=nobody
WorkingDirectory=/opt/campus
Environment=HOST=0.0.0.0
Environment=PORT=8080
Environment="NODE_NAME=Servidor NODE"
ExecStart=/usr/bin/python3 /opt/campus/server.py
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
[Install]
WantedBy=multi-user.target
SERVICE
systemctl daemon-reload
systemctl enable --now campus
python3 -c "import urllib.request,time; time.sleep(2); print(urllib.request.urlopen('http://127.0.0.1:8080/health').read())"
echo CAMPUS_BOOTSTRAP_OK
'''.replace('Servidor NODE', 'Servidor ' + node)
    if len(script.encode()) > 16384: raise ValueError('UserData excedeu 16 KiB')
    return {'Fn::Base64': script}

p = {
 'AmiId': {'Type': 'AWS::EC2::Image::Id', 'Description': 'AMI Amazon Linux 2023 STANDARD x86_64 na região do lab; não usar minimal/ARM.'},
 'InstanceType': param('Tipo x86_64 permitido no Academy.', Default='t3.micro', AllowedValues=['t3.micro','t2.micro','t3.small']),
 'AvailabilityZoneA': {'Type': 'AWS::EC2::AvailabilityZone::Name', 'Description': 'Primeira AZ da região.'},
 'AvailabilityZoneB': {'Type': 'AWS::EC2::AvailabilityZone::Name', 'Description': 'Segunda AZ, diferente da primeira.'},
 'AllowedWebCidr': param('IPv4 público da turma/rede em CIDR; 0.0.0.0/0 permite acesso público.', Default='0.0.0.0/0', AllowedPattern=r'(\d{1,3}\.){3}\d{1,3}/\d{1,2}'),
 'HttpsHost': param('Deixe vazio inicialmente. Depois de validar HTTPS, informe o hostname certificado para redirecionar HTTP.', Default='', AllowedPattern=r'^$|^[a-z0-9][a-z0-9.-]*\.[a-z]{2,}$')}
r = {}
r['Vpc'] = resource('EC2::VPC', {'CidrBlock':'10.0.0.0/16','EnableDnsSupport':True,'EnableDnsHostnames':True,'Tags':[{'Key':'Name','Value':sub('${AWS::StackName}-vpc')}]})
r['Igw'] = resource('EC2::InternetGateway', {})
r['IgwAttachment'] = resource('EC2::VPCGatewayAttachment', {'VpcId':ref('Vpc'),'InternetGatewayId':ref('Igw')})
for name,cidr,zone,public in [('PublicA','10.0.1.0/24','AvailabilityZoneA',True),('PublicB','10.0.2.0/24','AvailabilityZoneB',True),('PrivateA','10.0.11.0/24','AvailabilityZoneA',False),('PrivateB','10.0.12.0/24','AvailabilityZoneB',False)]:
    r[name] = resource('EC2::Subnet', {'VpcId':ref('Vpc'),'CidrBlock':cidr,'AvailabilityZone':ref(zone),'MapPublicIpOnLaunch':False,'Tags':[{'Key':'Name','Value':sub('${AWS::StackName}-'+name)}]})
r['PublicRoutes'] = resource('EC2::RouteTable', {'VpcId':ref('Vpc')})
r['PrivateRoutes'] = resource('EC2::RouteTable', {'VpcId':ref('Vpc')})
r['InternetRoute'] = resource('EC2::Route', {'RouteTableId':ref('PublicRoutes'),'DestinationCidrBlock':'0.0.0.0/0','GatewayId':ref('Igw')}, DependsOn='IgwAttachment')
for name in ['PublicA','PublicB','PrivateA','PrivateB']:
    r[name+'Association'] = resource('EC2::SubnetRouteTableAssociation', {'SubnetId':ref(name),'RouteTableId':ref('PublicRoutes' if name.startswith('Public') else 'PrivateRoutes')})
r['AlbSg'] = resource('EC2::SecurityGroup', {'VpcId':ref('Vpc'),'GroupDescription':'Entrada HTTP da turma; saida apenas para aplicacao.', 'SecurityGroupIngress':[{'IpProtocol':'tcp','FromPort':80,'ToPort':80,'CidrIp':ref('AllowedWebCidr')}], 'SecurityGroupEgress':[{'IpProtocol':'tcp','FromPort':8080,'ToPort':8080,'DestinationSecurityGroupId':ref('AppSg')}]})
r['AppSg'] = resource('EC2::SecurityGroup', {'VpcId':ref('Vpc'),'GroupDescription':'App privada sem acesso direto da internet.', 'SecurityGroupEgress':[{'IpProtocol':'tcp','FromPort':1,'ToPort':1,'CidrIp':'127.0.0.1/32','Description':'Regra sem destino remoto util para suprimir allow-all padrao.'}]})
r['AlbToApp'] = resource('EC2::SecurityGroupIngress', {'GroupId':ref('AppSg'),'SourceSecurityGroupId':ref('AlbSg'),'IpProtocol':'tcp','FromPort':8080,'ToPort':8080})
for node in ['A','B']:
    r['Server'+node] = resource('EC2::Instance', {'ImageId':ref('AmiId'),'InstanceType':ref('InstanceType'),'SubnetId':ref('Private'+node),'SecurityGroupIds':[ref('AppSg')],'UserData':user_data(node),'MetadataOptions':{'HttpTokens':'required','HttpEndpoint':'enabled'},'BlockDeviceMappings':[{'DeviceName':'/dev/xvda','Ebs':{'VolumeSize':8,'VolumeType':'gp3','Encrypted':True,'DeleteOnTermination':True}}],'Tags':[{'Key':'Name','Value':sub('${AWS::StackName}-servidor-'+node)}]})
r['Alb'] = resource('ElasticLoadBalancingV2::LoadBalancer', {'Scheme':'internet-facing','Type':'application','IpAddressType':'ipv4','Subnets':[ref('PublicA'),ref('PublicB')],'SecurityGroups':[ref('AlbSg')]}, DependsOn=['InternetRoute','PublicAAssociation','PublicBAssociation'])
r['Targets'] = resource('ElasticLoadBalancingV2::TargetGroup', {'VpcId':ref('Vpc'),'Protocol':'HTTP','Port':8080,'TargetType':'instance','HealthCheckPath':'/health','HealthCheckIntervalSeconds':10,'HealthCheckTimeoutSeconds':5,'HealthyThresholdCount':2,'UnhealthyThresholdCount':2,'Matcher':{'HttpCode':'200'},'TargetGroupAttributes':[{'Key':'deregistration_delay.timeout_seconds','Value':'10'},{'Key':'stickiness.enabled','Value':'false'}],'Targets':[{'Id':ref('ServerA')},{'Id':ref('ServerB')}]})
r['HttpListener'] = resource('ElasticLoadBalancingV2::Listener', {'LoadBalancerArn':ref('Alb'),'Protocol':'HTTP','Port':80,'DefaultActions':{'Fn::If':['UseHttps',[{'Type':'redirect','RedirectConfig':{'Protocol':'HTTPS','Port':'443','Host':ref('HttpsHost'),'StatusCode':'HTTP_301'}}],[{'Type':'forward','TargetGroupArn':ref('Targets')}]]}})
outputs = {'VpcId':ref('Vpc'),'AlbArn':ref('Alb'),'AlbDnsName':attr('Alb','DNSName'),'AlbHostedZoneId':attr('Alb','CanonicalHostedZoneID'),'AlbSecurityGroupId':ref('AlbSg'),'TargetGroupArn':ref('Targets'),'HttpUrl':sub('http://${Alb.DNSName}'),'ServerAId':ref('ServerA'),'ServerBId':ref('ServerB'),'PrivateIpA':attr('ServerA','PrivateIp'),'PrivateIpB':attr('ServerB','PrivateIp')}
write('01-base.yaml', template('Campus: VPC, quatro subnets, SGs, duas EC2 privadas e ALB.', p,r,outputs, Conditions={'UseHttps':{'Fn::Not':[{'Fn::Equals':[ref('HttpsHost'),'']}] }}, Rules={'DistinctZones':{'Assertions':[{'Assert':{'Fn::Not':[{'Fn::Equals':[ref('AvailabilityZoneA'),ref('AvailabilityZoneB')]}]},'AssertDescription':'Selecione duas zonas diferentes.'}]}}))

write('02-dns-privado.yaml',template('Route 53 privado: app.campus.internal resolve IPs privados das EC2.', {'VpcId':{'Type':'AWS::EC2::VPC::Id'},'PrivateIpA':param('Output PrivateIpA da base.'),'PrivateIpB':param('Output PrivateIpB da base.')}, {'Zone':resource('Route53::HostedZone',{'Name':'campus.internal','VPCs':[{'VPCId':ref('VpcId'),'VPCRegion':ref('AWS::Region')}]}),'Record':resource('Route53::RecordSet',{'HostedZoneId':ref('Zone'),'Name':'app.campus.internal','Type':'A','TTL':'30','ResourceRecords':[ref('PrivateIpA'),ref('PrivateIpB')]})},{'PrivateZoneId':ref('Zone'),'PrivateName':'app.campus.internal'}))

write('03-dns-publico.yaml',template('Zona publica para subdominio delegado pelo professor; nao registra dominio.', {'DelegatedDomain':param('Subdominio REAL sob seu controle, ex: grupo01.lab.seudominio.edu.br, sem ponto final.',AllowedPattern=r'^[a-z0-9][a-z0-9.-]*\.[a-z]{2,}$')}, {'Zone':resource('Route53::HostedZone',{'Name':ref('DelegatedDomain')})},{'PublicZoneId':ref('Zone'),'NameServers':{'Fn::Join':[', ',attr('Zone','NameServers')]},'PortalHostname':sub('eventos.${DelegatedDomain}')}))

write('04-certificado.yaml',template('ACM publico: executar somente depois da delegacao DNS publica.', {'PublicZoneId':param('ID da zona publica da stack 03, nesta conta.'),'PortalHostname':param('Output PortalHostname da stack 03.',AllowedPattern=r'^[a-z0-9][a-z0-9.-]*\.[a-z]{2,}$')}, {'Certificate':resource('CertificateManager::Certificate',{'DomainName':ref('PortalHostname'),'ValidationMethod':'DNS','DomainValidationOptions':[{'DomainName':ref('PortalHostname'),'HostedZoneId':ref('PublicZoneId')}],'CertificateTransparencyLoggingPreference':'ENABLED'})},{'CertificateArn':ref('Certificate')}))

p = {key:param(desc) for key,desc in {'AlbArn':'Output da stack base.','AlbDnsName':'Output da stack base.','AlbHostedZoneId':'CanonicalHostedZoneID do ALB (nao confundir com a zona do dominio).','AlbSecurityGroupId':'Output da base.','TargetGroupArn':'Output da base.','PublicZoneId':'ID da zona publica da stack 03.','PortalHostname':'Hostname usado no certificado.','CertificateArn':'Certificado ISSUED nesta conta e regiao.'}.items()}
p['AllowedWebCidr'] = param('Mesmo CIDR utilizado na base.',Default='0.0.0.0/0')
r = {'HttpsIngress':resource('EC2::SecurityGroupIngress',{'GroupId':ref('AlbSecurityGroupId'),'IpProtocol':'tcp','FromPort':443,'ToPort':443,'CidrIp':ref('AllowedWebCidr')}),'HttpsListener':resource('ElasticLoadBalancingV2::Listener',{'LoadBalancerArn':ref('AlbArn'),'Port':443,'Protocol':'HTTPS','SslPolicy':'ELBSecurityPolicy-TLS13-1-2-2021-06','Certificates':[{'CertificateArn':ref('CertificateArn')}],'DefaultActions':[{'Type':'forward','TargetGroupArn':ref('TargetGroupArn')}]}),'Alias':resource('Route53::RecordSet',{'HostedZoneId':ref('PublicZoneId'),'Name':ref('PortalHostname'),'Type':'A','AliasTarget':{'DNSName':ref('AlbDnsName'),'HostedZoneId':ref('AlbHostedZoneId'),'EvaluateTargetHealth':False}})}
write('05-https.yaml',template('Listener HTTPS e registro A Alias para ALB.',p,r,{'HttpsUrl':sub('https://${PortalHostname}')}))

vis = lambda name: {'CloudWatchMetricsEnabled':True,'SampledRequestsEnabled':True,'MetricName':name}
write('06-waf.yaml',template('WAF regional: demonstracao deterministica de bloqueio do prefixo /admin.', {'AlbArn':param('ARN do ALB, na mesma regiao da Web ACL.'),'RuleMode':param('Comece Count; atualize para Block para comparar.',Default='Count',AllowedValues=['Count','Block'])}, {'WebAcl':resource('WAFv2::WebACL',{'Scope':'REGIONAL','DefaultAction':{'Allow':{}},'VisibilityConfig':vis('CampusWebAcl'),'Rules':[{'Name':'AdminDemo','Priority':0,'Action':{'Fn::If':['BlockMode',{'Block':{}},{'Count':{}}]},'Statement':{'ByteMatchStatement':{'FieldToMatch':{'UriPath':{}},'PositionalConstraint':'STARTS_WITH','SearchString':'/admin','TextTransformations':[{'Priority':0,'Type':'URL_DECODE'},{'Priority':1,'Type':'LOWERCASE'}]}},'VisibilityConfig':vis('CampusAdminDemo')}]}),'Association':resource('WAFv2::WebACLAssociation',{'ResourceArn':ref('AlbArn'),'WebACLArn':attr('WebAcl','Arn')})},{'WebAclArn':attr('WebAcl','Arn')}, Conditions={'BlockMode':{'Fn::Equals':[ref('RuleMode'),'Block']}}))
print('6 templates gerados; UserData offline; aplicação incorporada a 01-base.yaml.')
