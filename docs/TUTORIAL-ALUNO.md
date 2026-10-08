# Tutorial do aluno — Campus na Nuvem

## Objetivo

Publicar o portal, identificar o caminho de uma requisição e testar isolamento, disponibilidade, DNS, HTTPS e bloqueio no WAF. A aplicação já está pronta. Use apenas dados fictícios.

**Antes de começar:** o professor deve confirmar as permissões e fornecer a região, a AMI Amazon Linux 2023 standard x86_64, duas zonas de disponibilidade e, para o percurso completo, uma zona pública delegada e um certificado ISSUED preparados na conta do seu grupo. Se esses itens não estiverem prontos, o tempo de 90 minutos não é garantido.

## 1. Obter os arquivos e abrir a conta

1. Clone o repositório indicado pelo professor ou extraia o ZIP.
2. Se já o clonou antes, execute `git pull --ff-only` na pasta. Não precisa programar ou executar o portal no computador para publicar na AWS.
3. Inicie o laboratório no AWS Academy pelo controle disponível na turma e aguarde a sessão estar pronta.
4. Abra o console AWS a partir do laboratório. Confira a região combinada com o professor em todas as telas regionais.
5. Use um prefixo exclusivo para suas stacks, por exemplo `campus-g01`. Cada grupo deve usar sua conta de laboratório. Em conta compartilhada, uma única zona privada `campus.internal` por VPC e nomes de stack exclusivos são essenciais.

Não cadastre uma conta pessoal nem tente ampliar permissões IAM para contornar o Academy. Se houver AccessDenied, anote ação e recurso e chame o professor.

## 2. Criar a infraestrutura principal

No CloudFormation, abra **Stacks → Create stack → With new resources (standard)**. Os rótulos podem variar com o idioma do console. Escolha **Choose an existing template → Upload a template file** e envie `infra/01-base.yaml`.

Use o nome `campus-g01-base` e preencha:

| Parâmetro | Valor |
|---|---|
| `AmiId` | ID fornecido pelo professor: AL2023 standard x86_64, na região atual. Não use AMI minimal/ARM. |
| `InstanceType` | `t3.micro` se permitido; use a alternativa validada pelo professor. |
| `AvailabilityZoneA` | Primeira AZ, por exemplo us-east-1a se essa for a região escolhida. |
| `AvailabilityZoneB` | Segunda AZ diferente, por exemplo us-east-1b. |
| `AllowedWebCidr` | IP público da rede em formato `/32`, se estável; `0.0.0.0/0` torna o portal acessível publicamente. |
| `HttpsHost` | Vazio nesta primeira etapa. |

Não selecione uma nova IAM role de execução. O projeto não cria roles nem exige marcar capacidade de criação de IAM. Preserve as demais opções padrão, revise e crie a stack. A sessão precisa ter permissão para provisionar os recursos.

Acompanhe **Events**, não apenas o status geral. Se falhar, encontre o primeiro evento CREATE_FAILED e consulte a seção de diagnóstico. **CREATE_COMPLETE não comprova que a aplicação iniciou**: ainda precisamos verificar os targets.

Enquanto aguarda, abra o template e identifique `Vpc`, `InternetRoute`, `AlbSg`, `AppSg`, `Targets` e `HttpListener`.

## 3. Verificar o portal e a rede

1. Em **Outputs**, abra `HttpUrl` usando `http://` explicitamente. Antes do certificado, não use HTTPS no endereço padrão do ALB.
2. Em **EC2 → Target Groups**, abra o target group cujo ARN aparece em `TargetGroupArn` e confira os dois targets em **healthy**. Aguarde a inicialização e os health checks.
3. No portal, clique várias vezes em **Nova requisição**. Observe Servidor A/B; não é obrigatório alternar a cada clique.
4. Em **VPC → Subnets/Route tables**, identifique:

| Subnet | CIDR | AZ | Tabela de rotas |
|---|---|---|---|
| PublicA | 10.0.1.0/24 | A | Rota local + 0.0.0.0/0 para IGW |
| PublicB | 10.0.2.0/24 | B | Rota local + 0.0.0.0/0 para IGW |
| PrivateA | 10.0.11.0/24 | A | Apenas rota local da VPC |
| PrivateB | 10.0.12.0/24 | B | Apenas rota local da VPC |

A VPC usa `10.0.0.0/16`. Um `/24` tem 256 endereços totais; em subnets IPv4 usuais da AWS, cinco são reservados. A subnet é pública pela rota ao IGW, não pelo seu nome nem pelo campo de autoatribuição de IP. As subnets públicas hospedam o ALB; as EC2 privadas não têm IP público e não têm saída geral para a internet.

5. Examine os Security Groups:

| Grupo | Entrada | Saída |
|---|---|---|
| ALB | TCP 80 do CIDR configurado; 443 será adicionada na stack HTTPS | TCP 8080 para o SG da aplicação |
| Aplicação | TCP 8080 apenas do SG do ALB | Sem permissão útil de iniciar conexões remotas; há uma regra TCP 1 para loopback que suprime o allow-all padrão |

O retorno das conexões permitidas funciona porque o SG é **stateful**. O DNS do AmazonProvidedDNS é uma exceção: não é filtrado por Security Groups, por isso a consulta privada funciona mesmo sem regra de saída DNS. Não generalize isso para outros servidores DNS.

6. Confira que as EC2 não possuem IP público nem regra SSH. O IP privado não é acessível diretamente do computador fora da VPC. Não tente “resolver” isso abrindo a porta 8080 ao mundo.

## 4. Testar continuidade do serviço

1. Faça capturas dos dois targets saudáveis e do portal.
2. Encontre a EC2 indicada no output `ServerAId`. Selecione **Instance state → Stop instance**. Não escolha Terminate.
3. Observe o estado no target group. A detecção não é instantânea; o target pode aparecer como unhealthy/unused conforme o estado da instância.
4. Após o ALB retirar esse target do atendimento, faça novas requisições. O Servidor B deve continuar atendendo. Algumas requisições podem falhar durante a transição; não estamos prometendo zero perda.
5. Inicie novamente a instância A e aguarde voltar a **healthy**.

Não desligue as duas. Com todos os targets indisponíveis, o ALB não consegue garantir atendimento; o comportamento de fail-open também pode encaminhar a targets não saudáveis quando todos falham.

## 5. Criar e testar DNS privado

Crie `campus-g01-dns-privado` enviando `infra/02-dns-privado.yaml`.

Copie os outputs da base para os parâmetros de mesmo nome: `VpcId`, `PrivateIpA` e `PrivateIpB`.

Após CREATE_COMPLETE:

1. Em Route 53 → Hosted zones, encontre `campus.internal`, tipo **Private**, e confira sua associação à VPC do laboratório.
2. Abra o registro A `app.campus.internal`: os dois valores são IPs privados das EC2.
3. No portal, clique **Consultar DNS privado**. A consulta é executada pelo servidor na VPC e deve retornar os IPs.
4. Diferencie isso de consultar no notebook: a zona não está publicada no DNS público. Não há VPN ou Resolver inbound endpoint neste projeto.

Esse registro não é um balanceador e não remove automaticamente um IP quando a EC2 para. O ALB é que usa health checks no fluxo público.

## 6. Inspecionar o DNS público e o ACM

**Etapa preparada pelo professor antes da aula**, ou feita por você em uma sessão prévia com tempo para propagação.

### 6.1 Zona pública

Envie `infra/03-dns-publico.yaml` para criar `campus-g01-dns-publico`. Em `DelegatedDomain`, informe o subdomínio real atribuído ao grupo, sem ponto final; por exemplo, `grupo01.lab.DOMINIO-DO-PROFESSOR`. Não copie esse exemplo literalmente.

Copie `NameServers` e envie ao professor. Ele deve criar um registro **NS para o subdomínio delegado** no DNS autoritativo do domínio pai, com todos os servidores retornados. Não substitua os NS do domínio inteiro. Criar uma hosted zone sozinha não publica a delegação e não registra um domínio.

Antes de continuar, o professor confirma que a delegação já resolve publicamente. Opcionalmente, use no seu computador:

```bash
nslookup -type=NS SEU_SUBDOMINIO_REAL
```

### 6.2 Certificado

Crie `campus-g01-certificado` com `infra/04-certificado.yaml`. Preencha `PublicZoneId` e `PortalHostname` com os outputs da stack DNS público.

CloudFormation pede o certificado e publica o CNAME de validação nessa zona Route 53. Em **ACM**, abra o certificado e confira nome, validação DNS e status **Issued**. A zona e o certificado devem estar na conta do grupo; o certificado deve estar na região do ALB.

Se continuar em **Pending validation**, confira a delegação pública e o CNAME. A stack pode permanecer em CREATE_IN_PROGRESS enquanto aguarda. Uma zona privada não valida certificado público. Não use o hostname `*.elb.amazonaws.com` do ALB para pedir seu certificado: você não controla esse domínio.

## 7. Habilitar HTTPS e o nome do portal

Envie `infra/05-https.yaml` para criar `campus-g01-https`. Preencha:

| Parâmetro | Fonte |
|---|---|
| `AlbArn`, `AlbDnsName`, `AlbHostedZoneId`, `AlbSecurityGroupId`, `TargetGroupArn` | Outputs da base |
| `PublicZoneId`, `PortalHostname` | Outputs de DNS público |
| `CertificateArn` | Output da stack certificado, já ISSUED |
| `AllowedWebCidr` | Mesmo CIDR usado na base |

**Não confunda `AlbHostedZoneId` (identificador canônico do ALB) com `PublicZoneId` (zona do seu domínio).**

Após CREATE_COMPLETE, abra o output `HttpsUrl`. Verifique o certificado no navegador, o hostname e a indicação HTTPS no portal. No console, localize o listener 443 e o registro **A Alias** apontando ao ALB.

Agora ative o redirecionamento: na stack **base**, escolha **Update → Use existing template** e altere somente `HttpsHost` para o `PortalHostname`. Preserve AMI, AZs e demais parâmetros. Revise as alterações e execute. Acesse novamente a URL HTTP: deve redirecionar para o hostname HTTPS válido.

O certificado protege navegador → ALB. ALB → EC2 continua em HTTP 8080 neste exercício.

## 8. Aplicar WAF: observar e bloquear

1. Antes do WAF, abra `/admin` no seu portal. Deve retornar HTTP 200 e uma mensagem fictícia; não há painel administrativo real.
2. Crie `campus-g01-waf` com `infra/06-waf.yaml`, passando `AlbArn` da base e `RuleMode=Count`.
3. Em WAF, selecione a região correta. Abra a Web ACL e confirme a associação ao ALB e a regra `AdminDemo`.
4. Acesse `/admin` algumas vezes. **Count** registra a correspondência, mas permite a requisição. Métricas/amostras podem levar alguns minutos para aparecer.
5. Atualize a stack WAF, mantendo o template, com `RuleMode=Block`.
6. Após a propagação da regra, abra `/admin`: deve retornar **403 Forbidden**. A página principal e `/health` devem continuar acessíveis.
7. Registre evidências de antes/depois e da associação ao ALB.

O filtro bloqueia URIs cujo caminho começa por `/admin`, após URL decode e lowercase; isso inclui `/admin123`. É intencional e didático. Não é um conjunto completo de proteção contra ataques e não substitui autenticação/autorização. Não faça testes contra sistemas externos.

Opcional: com Python no computador, execute usando a URL HTTPS final (ou HTTP antes de habilitar HTTPS):

```bash
python3 scripts/check_portal.py https://SEU_HOSTNAME --admin-status 403
```

Antes de ativar Block, use `--admin-status 200`. O script verifica saúde, agenda, respostas dos servidores e status de `/admin`; não exige que ambos os servidores apareçam em poucas requisições.

## 9. Entrega do grupo

Preencha [EVIDENCIAS.md](EVIDENCIAS.md). Inclua capturas de: topologia/rotas, SGs, targets antes/depois da parada, DNS privado, A Alias público, certificado válido, WAF Count/Block e exclusão.

Explique: por que uma EC2 privada atende a usuários da internet através do ALB? Por que um registro DNS privado não habilita HTTPS público? Qual a diferença entre SG e WAF? O que o CloudFormation automatizou?

## 10. Limpeza obrigatória

Use apenas os recursos e stacks do seu grupo. Não remova zonas ou registros de terceiros.

1. Se for manter a base temporariamente, atualize `HttpsHost` para vazio antes de excluir HTTPS. Se excluir tudo imediatamente, pode seguir a ordem abaixo.
2. Exclua `campus-g01-waf`; aguarde a associação e a ACL desaparecerem.
3. Exclua `campus-g01-https`; aguarde a remoção de listener, regra 443 e A Alias.
4. Exclua `campus-g01-certificado` e aguarde.
5. Na zona pública exclusiva do grupo, verifique se restou o CNAME de validação ACM (ele pode permanecer após a exclusão do certificado). Remova apenas esse CNAME e outros registros adicionados manualmente pelo seu grupo. Não tente apagar NS/SOA padrão.
6. Peça ao professor para retirar a delegação NS do seu subdomínio no domínio pai antes de liberar a zona. Depois exclua `campus-g01-dns-publico`.
7. Exclua `campus-g01-dns-privado` antes de excluir a VPC.
8. Exclua `campus-g01-base`. Verifique DELETE_COMPLETE; ALB/interfaces podem levar vários minutos para desaparecer.
9. Confira que não restaram EC2, EBS, ALB, Web ACL ou hosted zones do exercício. Se houver DELETE_FAILED, abra Events, corrija a dependência e tente novamente. Só então encerre a sessão do Academy.

Se o professor manteve as stacks DNS/certificado para outra aula, siga a orientação dele e registre que esses recursos continuam ativos e podem gerar custo. Encerrar a sessão não equivale a excluir toda a infraestrutura.

## Diagnóstico rápido

| Sintoma | Verificar |
|---|---|
| AccessDenied | Ação e recurso no evento; restrições do Academy. CloudFormation não ignora essas restrições. |
| AMI inexistente ou arquitetura incompatível | AMI na região correta; AL2023 standard x86_64 e tipo permitido. |
| ALB demora/targets unhealthy | AMI, inicialização, SG 8080, `/health`. Em EC2 → Monitor and troubleshoot → Get system log, procure `CAMPUS_BOOTSTRAP_OK` ou erro de Python/serviço. Pode haver atraso no log. |
| CREATE_COMPLETE, mas portal não abre | Confira targets; base não utiliza cfn-signal nem garante prontidão da aplicação. Verifique CIDR de origem e listener. |
| HTTP 503 | Ausência de targets disponíveis/registrados; confira EC2 e target group. |
| HTTPS no DNS padrão do ALB dá erro | Use o hostname coberto pelo certificado; o domínio padrão do ALB não está nele. |
| Certificado pendente | Delegação NS, CNAME público, zona correta e tempo de propagação. |
| DNS privado falha | Stack 02, associação com VPC e DNS support/hostnames. Teste pelo botão do portal. |
| WAF não bloqueia | Região, associação, RuleMode=Block e tempo de propagação. |
| Zona pública não exclui | Remova CNAME ACM residual/registros manuais exclusivos do lab; preserve NS/SOA. |
| Atualização da app não aparece | `git pull` só muda os arquivos locais. Gere o template atualizado e recrie o ambiente; UserData não é mecanismo contínuo de deploy. |
