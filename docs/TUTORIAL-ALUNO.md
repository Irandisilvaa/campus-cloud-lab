# Campus na Nuvem — tutorial reproduzível no AWS Academy

> **Trilha principal validada por execução acompanhada em 08/10/2026:** CloudFormation → VPC/EC2/ALB → falha e recuperação → Route 53 privado → WAF Count/Block → evidências → limpeza. O relato foi fornecido pelo operador do AWS Academy, não por acesso administrativo à conta. DNS público, ACM e HTTPS **não foram executados** por falta de domínio controlado. Os testes de rotas e Security Groups ainda exigem conferência com os comandos abaixo.

**Público:** alunos e professores de Redes, Computação em Nuvem e Segurança. **Tempo:** reserve pelo menos 90 minutos, com margem para a AWS provisionar/excluir recursos. **Custo:** o laboratório consome créditos; não deixe recursos ativos ao final. **Não há garantia de execução em toda conta Academy:** permissões, cotas e disponibilidade variam.

## 0. O que construiremos

- Um portal de três eventos fictícios, com `/health`, `/api/eventos`, `/api/status`, `/api/dns` e `/admin` (fictício).
- VPC `10.0.0.0/16`; duas sub-redes públicas (`10.0.1.0/24`, `10.0.2.0/24`) e duas privadas (`10.0.11.0/24`, `10.0.12.0/24`), em duas zonas de disponibilidade.
- Duas EC2 Amazon Linux 2023 **standard x86_64** (`t3.micro`, quando permitido), sem IP público, servidor Python na porta 8080, iniciadas por UserData.
- Um Application Load Balancer público na porta 80, com health check `/health`; Security Groups restringem a comunicação do ALB para as EC2.
- Uma zona privada `campus.internal`, registro `app.campus.internal` para os IPs privados das EC2, e uma Web ACL WAF com `Count` → `Block` em `/admin`.

**Não usamos:** domínio real, HTTPS, ACM, Auto Scaling, NAT Gateway, SSH, banco ou credenciais nas EC2. Não marque esses itens como executados.

## 1. Abrir a sessão e conferir pré-requisitos

1. Entre no **AWS Academy / Learner Lab**, clique em **Start Lab** e espere o ambiente iniciar. Abra o console AWS pelo link do próprio laboratório.
2. No canto superior direito, confirme a região do professor. No ensaio foi utilizada **US East (N. Virginia) `us-east-1`**.
3. Abra **CloudShell**. Não crie usuário, política nem IAM Role. O CloudFormation deve executar com as permissões permitidas pela sessão do laboratório.
4. Cada grupo deve trabalhar em sua **própria conta de laboratório**, sempre que possível. Em conta compartilhada, mantenha um `PREFIX` exclusivo por grupo e verifique cotas.
5. Identifique uma AMI **Amazon Linux 2023 standard x86_64** para a região; não use AMI minimal/ARM. O comando abaixo usa o parâmetro público da AWS e pode falhar por restrição `ssm:GetParameter`; nesse caso o professor informa a AMI ou consulta a imagem pelo console EC2.

Cole este bloco uma única vez no CloudShell, trocando **somente** `campus-g01` pelo prefixo exclusivo do seu grupo:

```bash
export AWS_PAGER=""                    # impede a tela de ajuda/paginação do less
export AWS_DEFAULT_REGION="us-east-1"  # use a região definida pelo professor
PREFIX="campus-g01"                    # exemplo: campus-g02, campus-g03...
BASE="${PREFIX}-base"
DNS="${PREFIX}-dns-privado"
WAF="${PREFIX}-waf"

aws sts get-caller-identity --query '{Account:Account,Arn:Arn}' --output table
aws ec2 describe-availability-zones --filters Name=state,Values=available --query 'AvailabilityZones[].ZoneName' --output table

AMI=$(aws ssm get-parameter --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 --query Parameter.Value --output text) || AMI=""
echo "AMI oficial (se autorizada): ${AMI:-CONSULTE O PROFESSOR}"
```

Escolha **duas AZs distintas** da lista (o sufixo `1a` de uma conta não garante localização física idêntica à de outra). Exemplo para região `us-east-1`, **somente se ambas aparecerem disponíveis**:

```bash
AZ_A="us-east-1a"
AZ_B="us-east-1b"
# Se a consulta SSM falhou, substitua por uma AMI x86_64 standard validada pelo professor:
# AMI="ami-xxxxxxxxxxxxxxxxx"
test -n "$AMI" && test "$AZ_A" != "$AZ_B" || echo "ATENÇÃO: configure AMI e duas AZs distintas antes de criar."
```

**Antes de continuar**, confirme `AMI` não vazia, duas AZs realmente disponíveis e a região correta. Não copie AMIs, IDs de VPC, de EC2 ou IPs de outros alunos.

## 2. CloudFormation: criar a pilha base

### Caminho pelo console (o mesmo usado no ensaio)

Em **CloudFormation → Pilhas → Criar pilha → Com novos recursos (padrão)**, escolha **Carregar arquivo de modelo** `infra/01-base.yaml`, baixado de [infra/01-base.yaml](../infra/01-base.yaml). Na tela de parâmetros:

| Campo | Valor |
|---|---|
| Nome | `${PREFIX}-base`, substituindo a variável pelo prefixo literal do grupo (por exemplo `campus-g01-base`) |
| AmiId | AMI AL2023 standard x86_64 válida nesta região |
| InstanceType | `t3.micro` (se autorizado) |
| AvailabilityZoneA e B | Duas AZs diferentes e disponíveis |
| AllowedWebCidr | `0.0.0.0/0` para a demonstração pública; restrinja ao IP `/32` da turma quando possível |
| HttpsHost | **Vazio** |

Em **Configurar opções**: etiquetas opcionais `Projeto=CampusNaNuvem`; **Perfil do IAM: em branco** (não clique em “Criar novo perfil”); modo expresso desabilitado; em caso de falha, reverter recursos; manter validações; sem política especial, SNS ou proteção contra encerramento. Revise e crie. Se a interface exigir um perfil, **não improvise uma role**: consulte o professor sobre as permissões/role já permitida pelo Learner Lab.

### Caminho alternativo pelo CloudShell

Os comandos abaixo são alternativa ao console, **não execute os dois métodos criando a mesma stack**. A criação começa a consumir créditos.

```bash
curl -fsSL https://raw.githubusercontent.com/Irandisilvaa/campus-cloud-lab/main/infra/01-base.yaml -o /tmp/01-base.yaml
: "${AMI:?Defina uma AMI AL2023 standard x86_64}"
: "${AZ_A:?Defina a primeira AZ}"
: "${AZ_B:?Defina a segunda AZ}"
test "$AZ_A" != "$AZ_B" || { echo 'AZs devem ser diferentes'; exit 1; }

aws cloudformation create-stack --stack-name "$BASE" \
  --template-body file:///tmp/01-base.yaml \
  --parameters \
    ParameterKey=AmiId,ParameterValue="$AMI" \
    ParameterKey=InstanceType,ParameterValue=t3.micro \
    ParameterKey=AvailabilityZoneA,ParameterValue="$AZ_A" \
    ParameterKey=AvailabilityZoneB,ParameterValue="$AZ_B" \
    ParameterKey=AllowedWebCidr,ParameterValue=0.0.0.0/0 \
    ParameterKey=HttpsHost,ParameterValue="" \
  --tags Key=Projeto,Value=CampusNaNuvem
aws cloudformation wait stack-create-complete --stack-name "$BASE"
```

No console, acompanhe **Eventos** até `CREATE_COMPLETE` (o estado inicial é `CREATE_IN_PROGRESS`). Se ocorrer `CREATE_FAILED`/rollback, copie **o primeiro recurso que falhou** e o motivo; pare antes das próximas pilhas. `CREATE_COMPLETE` não prova que o servidor Python está pronto.

## 3. Teste do portal, API e balanceamento

Para ambos os métodos de criação, abra CloudShell e carregue os Outputs da **sua própria** stack:

```bash
URL=$(aws cloudformation describe-stacks --stack-name "$BASE" --query "Stacks[0].Outputs[?OutputKey=='HttpUrl'].OutputValue | [0]" --output text)
TG=$(aws cloudformation describe-stacks --stack-name "$BASE" --query "Stacks[0].Outputs[?OutputKey=='TargetGroupArn'].OutputValue | [0]" --output text)
A=$(aws cloudformation describe-stacks --stack-name "$BASE" --query "Stacks[0].Outputs[?OutputKey=='ServerAId'].OutputValue | [0]" --output text)
B=$(aws cloudformation describe-stacks --stack-name "$BASE" --query "Stacks[0].Outputs[?OutputKey=='ServerBId'].OutputValue | [0]" --output text)
VPC=$(aws cloudformation describe-stacks --stack-name "$BASE" --query "Stacks[0].Outputs[?OutputKey=='VpcId'].OutputValue | [0]" --output text)
ALB_ARN=$(aws cloudformation describe-stacks --stack-name "$BASE" --query "Stacks[0].Outputs[?OutputKey=='AlbArn'].OutputValue | [0]" --output text)
IP_A=$(aws cloudformation describe-stacks --stack-name "$BASE" --query "Stacks[0].Outputs[?OutputKey=='PrivateIpA'].OutputValue | [0]" --output text)
IP_B=$(aws cloudformation describe-stacks --stack-name "$BASE" --query "Stacks[0].Outputs[?OutputKey=='PrivateIpB'].OutputValue | [0]" --output text)
echo "Portal HTTP: $URL"
echo "EC2 A: $A / $IP_A | EC2 B: $B / $IP_B"
```

Abra o `HttpUrl` no navegador **com `http://`**. O portal deve exibir os três eventos e a área **A nuvem em funcionamento**. Depois rode:

```bash
curl -fsS "$URL/health"; echo
curl -fsS "$URL/api/eventos" | python3 -m json.tool
for i in {1..12}; do curl -fsS "$URL/api/status" | python3 -c 'import json,sys;print(json.load(sys.stdin)["server"])'; done
aws elbv2 describe-target-health --target-group-arn "$TG" --query 'TargetHealthDescriptions[].{Instancia:Target.Id,Estado:TargetHealth.State}' --output table
```

**Esperado:** `/health` contém `"status":"ok"`; `/api/eventos` tem três eventos; A e B podem aparecer entre as chamadas (não precisa alternar a cada clique); target group mostra **2 `healthy`**. Se estiver `initial`, aguarde e consulte novamente. Se houver 503, procure os eventos, a AMI, a porta 8080 e os logs de sistema da instância.

## 4. Comprovar rede e isolamento (sem alterar recursos)

```bash
aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC" --query 'Subnets[].{ID:SubnetId,CIDR:CidrBlock,Zona:AvailabilityZone,IPPublicoAutomatico:MapPublicIpOnLaunch}' --output table
aws ec2 describe-route-tables --filters "Name=vpc-id,Values=$VPC" --query 'RouteTables[].{Tabela:RouteTableId,Subnets:Associations[].SubnetId,Rotas:Routes[].{Destino:DestinationCidrBlock,Gateway:GatewayId}}' --output json
aws ec2 describe-security-groups --filters "Name=vpc-id,Values=$VPC" --query 'SecurityGroups[].{Nome:GroupName,ID:GroupId,Entrada:IpPermissions,Saida:IpPermissionsEgress}' --output json
aws ec2 describe-instances --instance-ids "$A" "$B" --query 'Reservations[].Instances[].{ID:InstanceId,Estado:State.Name,Privado:PrivateIpAddress,Publico:PublicIpAddress,Subnet:SubnetId}' --output table
```

**Verifique, não apenas execute:** quatro subnets `/24`; somente as públicas têm `0.0.0.0/0` para o Internet Gateway; as privadas só têm rota local; ALB recebe TCP 80 e envia TCP 8080 ao SG da aplicação; EC2 recebe TCP 8080 **somente** do SG do ALB; **sem SSH público**; ambas EC2 estão `running` e `Publico: None`. Desabilitamos `less` com `AWS_PAGER=""`: se você cair numa tela de ajuda, pressione `q` e confira essa variável.

## 5. Testar falha e recuperação — com cuidado

**Faça isto somente se ambos targets estão `healthy`.** O ensaio acompanhou a parada do **Servidor B**, que inicialmente gerou uma resposta 504 durante a transição e depois deixou o Servidor A atendendo. O erro transitório não representa “alta disponibilidade perfeita”.

```bash
# Interrompa APENAS B (não termine; não pare as duas)
aws ec2 stop-instances --instance-ids "$B"
aws ec2 wait instance-stopped --instance-ids "$B"
aws elbv2 describe-target-health --target-group-arn "$TG" --query 'TargetHealthDescriptions[].{Instancia:Target.Id,Estado:TargetHealth.State}' --output table
# Aguarde o alvo B estar unused/unhealthy; a detecção não é instantânea.
for i in {1..10}; do curl -sS -o /dev/null -w 'HTTP %{http_code}\n' "$URL/api/status"; done
```

**Esperado depois da detecção:** a maioria/todas as chamadas respondem 200 pelo A; pode ocorrer erro 504 durante transição. Selecione `/api/status` para identificar o nome do servidor. **Recupere B antes de avançar:**

```bash
aws ec2 start-instances --instance-ids "$B"
aws ec2 wait instance-running --instance-ids "$B"
aws elbv2 describe-target-health --target-group-arn "$TG" --query 'TargetHealthDescriptions[].{Instancia:Target.Id,Estado:TargetHealth.State}' --output table
# Se B estiver initial, espere alguns minutos e repita até haver 2 healthy.
```

O ALB redireciona tráfego para targets disponíveis; **não cria novas EC2** (não há Auto Scaling).

## 6. Criar o Route 53 privado — sem domínio comprado

Antes desta stack, `curl -s -o /dev/null -w '%{http_code}\n' "$URL/api/dns"` normalmente retorna **503**, pois o nome ainda não existe.

```bash
curl -fsSL https://raw.githubusercontent.com/Irandisilvaa/campus-cloud-lab/main/infra/02-dns-privado.yaml -o /tmp/02-dns-privado.yaml
aws cloudformation create-stack --stack-name "$DNS" \
  --template-body file:///tmp/02-dns-privado.yaml \
  --parameters \
    ParameterKey=VpcId,ParameterValue="$VPC" \
    ParameterKey=PrivateIpA,ParameterValue="$IP_A" \
    ParameterKey=PrivateIpB,ParameterValue="$IP_B"
aws cloudformation wait stack-create-complete --stack-name "$DNS"
curl -fsS "$URL/api/dns" | python3 -m json.tool
```

**Esperado:** `name: app.campus.internal`, `addresses` contendo exatamente os IPs privados A/B da **sua** stack. Confira no console **Route 53 → Hosted zones → campus.internal (Private)**. A resolução é feita no servidor dentro da VPC, não no notebook do estudante. A zona privada **não** habilita HTTPS público.

## 7. Criar AWS WAF, observar e bloquear

O WAF pode ter **restrições e cobrança** próprias. Se não houver permissão WAFv2, registre o `AccessDenied` no relatório; não tente criar IAM Role/políticas nem trocar para uma conta pessoal.

```bash
curl -fsSL https://raw.githubusercontent.com/Irandisilvaa/campus-cloud-lab/main/infra/06-waf.yaml -o /tmp/06-waf.yaml
aws cloudformation create-stack --stack-name "$WAF" \
  --template-body file:///tmp/06-waf.yaml \
  --parameters ParameterKey=AlbArn,ParameterValue="$ALB_ARN" ParameterKey=RuleMode,ParameterValue=Count
aws cloudformation wait stack-create-complete --stack-name "$WAF"
curl -sS -o /dev/null -w 'Admin: HTTP %{http_code}\n' "$URL/admin"  # esperado 200
```

Agora atualize a **mesma** pilha (não crie outra) para `Block`:

```bash
aws cloudformation update-stack --stack-name "$WAF" --use-previous-template \
  --parameters ParameterKey=AlbArn,UsePreviousValue=true ParameterKey=RuleMode,ParameterValue=Block
aws cloudformation wait stack-update-complete --stack-name "$WAF"
aws wafv2 get-web-acl-for-resource --resource-arn "$ALB_ARN" \
  --query 'WebACL.{Nome:Name,Regras:Rules[].{Nome:Name,Acao:Action}}' --output json
```

A regra `AdminDemo` deve mostrar `"Block": {}`. **Importante:** no ensaio, logo após `UPDATE_COMPLETE`, `/admin` ainda respondeu **200** por um período. Isso **não significa necessariamente falha**: aguarde a propagação e repita:

```bash
for i in {1..6}; do
  echo "Tentativa $i"
  curl -sS -o /dev/null -w 'Admin: HTTP %{http_code}\n' "$URL/admin"
  curl -sS -o /dev/null -w 'Portal: HTTP %{http_code}\n' "$URL/"
  sleep 20
done
```

**Esperado:** `/admin` passa a **403**, mas `/` continua **200**. No console AWS WAF, confira a Web ACL regional associada ao ALB e sua regra `AdminDemo`. Uma proteção didática de URI **não substitui** autenticação ou políticas de segurança de produção.

## 8. HTTPS e ACM: exercício **não executado sem domínio**

**Pare aqui quanto a DNS público e certificado se não tiver controle de domínio/subdomínio real.** Não crie uma zona pública inventada nem peça certificado para `*.elb.amazonaws.com`: você não controla esses nomes. Registre **NÃO EXECUTADO — falta de domínio público para validar ACM/HTTPS**, e não “reprovado” ou “aprovado”. Os templates `03-dns-publico.yaml`, `04-certificado.yaml` e `05-https.yaml` permanecem no repositório como percurso avançado **condicional**, que exige professor com delegação de DNS e certificado ISSUED; não foi validado no ensaio relatado.

## 9. Evidências e respostas

Antes da limpeza, faça capturas do CloudFormation, portal, Target Group antes/durante/depois da parada, subnets/rotas, Security Groups, EC2 sem IP público, resposta `/api/dns` e WAF Count/Block. Preencha [EVIDENCIAS.md](EVIDENCIAS.md). Não publique credenciais, tokens ou logs completos da sessão. Explique por que EC2 privadas respondem via ALB; o que torna uma subnet pública; diferença entre SG/WAF; e por que DNS privado não fornece certificado HTTPS público.

## 10. Limpeza obrigatória após registrar evidências

**Exclua apenas stacks do seu prefixo.** Ordem do percurso sem domínio: **WAF → DNS privado → Base**. Antes, confira as três pilhas existentes. Se algum serviço foi negado e a stack não existe ou está em rollback, confira o status antes de tentar exclusão.

```bash
aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE ROLLBACK_COMPLETE --query "StackSummaries[?starts_with(StackName, '${PREFIX}')].[StackName,StackStatus]" --output table
# Execute os comandos a seguir apenas para stacks que realmente existem e pertencem ao grupo:
aws cloudformation delete-stack --stack-name "$WAF"
aws cloudformation wait stack-delete-complete --stack-name "$WAF"
aws cloudformation delete-stack --stack-name "$DNS"
aws cloudformation wait stack-delete-complete --stack-name "$DNS"
aws cloudformation delete-stack --stack-name "$BASE"
aws cloudformation wait stack-delete-complete --stack-name "$BASE"
```

Confira na conta que ALB, EC2, volumes e zona privada **do seu grupo** foram realmente excluídos. `DELETE_FAILED` exige diagnóstico de dependências em Eventos; **encerrar o Learner Lab ou parar EC2 não limpa o resto**. Se você criou HTTPS público em outra versão, a ordem de limpeza é diferente: siga a documentação específica e remova recursos opcionais/delegações antes da VPC.

## 11. Problemas mais comuns

| Sintoma | Ação segura |
|---|---|
| `less`/tela de ajuda no terminal | Pressione `q`; `export AWS_PAGER=""` |
| `AccessDenied` / quota | Registre operação negada e consulte professor; não altere IAM por conta própria |
| AMI não aparece / arquitetura incompatível | Use AL2023 **standard x86_64** da mesma região; confirme instância permitida |
| Stack `CREATE_COMPLETE`, portal sem resposta | Aguarde health checks, inspecione Target Group e log de boot (`CAMPUS_BOOTSTRAP_OK`) |
| Target `initial` | Aguarde; não marque falha enquanto inicializa |
| Um 504 no teste de parada | Pode ocorrer durante transição; só avalie após o ALB detectar o target parado |
| `start-instances` retorna `running` mas ainda `initial` no ALB | Espere novos health checks até `healthy` |
| `/api/dns` 503 | Ainda não criou a stack 02, zona privada incorreta ou VPC não associada |
| `/admin` 200 logo após mudar para Block | Confirme Web ACL associada, `AdminDemo: Block`; aguarde propagação e tente novamente |
| HTTPS indisponível | Sem domínio controlado, mantenha HTTP e documente limite; não peça ACM para o DNS padrão do ALB |
| `DELETE_FAILED` | Verifique Eventos e dependências; não apague recursos de outros grupos |

### Entrega final

Envie **[EVIDENCIAS.md](EVIDENCIAS.md)** preenchido, capturas com resultados reais, explicações dos conceitos e comprovação de exclusão. A utilização de AWS Academy é sujeita às permissões/cotas de cada turma: **não prometa 100% de execução sem novo ensaio no ambiente da turma**.
