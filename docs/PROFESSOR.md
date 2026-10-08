# Guia do professor — Campus na Nuvem / AWS Academy

## Situação confirmada do projeto

Um **ensaio acompanhado em 08/10/2026**, com saídas de CloudShell fornecidas pelo operador, confirmou a trilha **sem domínio**: pilha base, portal/API, dois targets saudáveis, interrupção/recuperação de uma EC2, Route 53 privado e WAF Count → Block (após propagação). **Não** foram comprovados na mesma evidência os detalhes finais de route tables/SG nem a limpeza de todas as stacks. **DNS público, ACM e HTTPS não foram executados** por ausência de domínio público controlado. Ver [VALIDACAO.md](VALIDACAO.md).

A execução bem-sucedida em um Learner Lab **não garante** os mesmos resultados em todas as contas: quotas, AMIs, AZs e políticas do Academy podem mudar. Faça um ensaio **na mesma modalidade e região da turma** antes da aula. Consulte o [tutorial do aluno](TUTORIAL-ALUNO.md) para os comandos efetivamente utilizados.

## Preparação obrigatória da turma

1. Confirme que os estudantes têm **AWS Academy Learner Lab** autorizado, região definida (ensaio: `us-east-1`) e créditos suficientes.
2. Confira permissão para **CloudFormation, VPC/EC2, ELBv2, Route 53 private hosted zone e WAFv2 regional**; não crie policies/roles para contornar bloqueios da conta.
3. Valide duas AZs distintas, tipo `t3.micro` (ou alternativa prevista no template), AMI **AL2023 standard x86_64**, e capacidade para duas EC2, dois volumes e um ALB por grupo.
4. Peça um **prefixo exclusivo** (`campus-g01`, `campus-g02`...). As pilhas serão `<prefixo>-base`, `<prefixo>-dns-privado` e `<prefixo>-waf`.
5. Preferencialmente **uma conta Learner Lab por grupo**; em conta compartilhada, analise quotas e conflitos antes de provisionar. Nunca compartilhe credenciais entre grupos.
6. Baixe/teste os YAML em `infra/`. Em CloudShell, os alunos também podem obtê-los via `curl` dos links `raw.githubusercontent.com` do repositório.
7. Prepare plano para `AccessDenied` e para alunos com conexão restrita: demonstração prévia e registro de serviço não executado; não prometa 100% de compatibilidade.
8. Prepare capturas orientadas por [EVIDENCIAS.md](EVIDENCIAS.md) e tempo para limpeza da AWS.

## Execução sugerida

| Intervalo aproximado | Atividade |
|---|---|
| 0–15 min | Teoria: VPC/CIDR, AZ/subnets/rotas, EC2, SG, ALB, DNS, WAF e IaC |
| 15–30 min | Login, região/AMI/AZs, `01-base.yaml`, parâmetros e CloudFormation |
| 30–45 min | Portal, `/health`, targets `healthy`, comandos de rede e isolamento |
| 45–55 min | Parar **apenas uma** EC2 e recuperar; explicar HTTP 504 transitório |
| 55–65 min | `02-dns-privado.yaml`: `/api/dns` de 503 para resolução interna |
| 65–80 min | `06-waf.yaml`: Count/200 → Block/403 com espera pela propagação |
| 80–90+ min | Capturas, questões, exclusão das 3 stacks e confirmação |

As esperas de provisionamento/exclusão e propagação podem ultrapassar esse tempo; o cronograma é **estimativa**, não garantia. Não deixe o encerramento para depois que os créditos acabarem.

## Ponto de atenção: Console CloudFormation

Na criação da stack base, deixe **Perfil do IAM** sem selecionar; **não clique em “Criar novo perfil”**. Preserve validações de implantação, sem modo expresso e sem proteção contra encerramento na pilha didática; o parâmetro `HttpsHost` permanece **vazio** na trilha sem domínio. `CREATE_COMPLETE` não basta: valide portal e targets. No CloudShell, use `export AWS_PAGER=""` para evitar o paginador `less` que confundiu a leitura de testes na execução acompanhada.

## Ponto de atenção: falha e WAF

O ensaio parou B: A respondeu nove de dez chamadas, com **um HTTP 504 durante a transição**, e B retornou a `healthy` depois de reiniciada. Explique falha parcial, health checks e recuperação; **não prometa disponibilidade de 100%** e não confunda ALB com Auto Scaling.

No WAF, o retorno `/admin` permaneceu 200 imediatamente após o CloudFormation concluir `UPDATE_COMPLETE`, mas passou para 403 após propagação. Confira a Web ACL **associada ao ALB**, `AdminDemo` em **Block**, repita até estabilizar e mantenha `/` respondendo 200. WAF é proteção de aplicação por URI; SG é controle de rede/porta.

## HTTPS público: módulo avançado **condicional e não validado no ensaio**

Os templates `03-dns-publico.yaml`, `04-certificado.yaml` e `05-https.yaml` estão no repositório, **mas não fazem parte da trilha principal reproduzida**. Para oferecer a extensão, é indispensável controlar um domínio/subdomínio público real, delegar os NS no DNS autoritativo e obter ACM **ISSUED na mesma conta e região do ALB**. Prepare DNS/ACM previamente por grupo; o endereço `*.elb.amazonaws.com` **não pode ser certificado como se fosse seu domínio**. Sem domínio, registre **não executado** em vez de declarar HTTPS aprovado. Caso opte pelo módulo avançado, use as instruções abaixo e ensaie previamente:

1. Criar zona pública do subdomínio do grupo via `infra/03-dns-publico.yaml`.
2. Delegar o subdomínio no DNS pai com os `NameServers` do Output; verificar resolução pública.
3. Criar `infra/04-certificado.yaml` com `PublicZoneId` e `PortalHostname` e aguardar certificado `ISSUED`.
4. Criar `infra/05-https.yaml` usando Outputs da base, zona pública e certificado (não confundir `AlbHostedZoneId` com `PublicZoneId`).
5. Conferir o `HttpsUrl` e listener 443 antes de atualizar a base: `HttpsHost` recebe o hostname para redirecionamento HTTP → HTTPS.
6. Para limpar esse módulo, remover WAF, listener/alias HTTPS, certificado, CNAME de validação manual residual, delegação/zona pública, DNS privado e **por último** a base. Não apagar registros de terceiros.

Sem domínio, **não execute** essas três stacks; deixe `HttpsHost` vazio.

## Custos, segurança e avaliação

O laboratório pode consumir créditos por EC2/EBS, ALB/IPv4, hosted zone e WAF. WAF e zonas podem ter características de cobrança distintas de minutos; valide precificação/quotas para a turma. Não use contas pessoais para contornar falta de crédito/permissão. Não é produção: não há autenticação, banco, Auto Scaling, NAT ou SSH e a aplicação usa servidor Python didático.

Peça que os alunos **comprovem** rotas públicas/privadas, SG para porta 8080, dois targets saudáveis, comportamento durante parada/recuperação, DNS privado e WAF antes/depois, e a limpeza. Os resultados precisam ser da conta de cada grupo. Não publicar chaves, tokens ou capturas com dados de acesso.

## Atualização do repositório

O repositório já está publicado em `https://github.com/Irandisilvaa/campus-cloud-lab`. A cópia local é obtida por `git clone` ou atualizada via `git pull --ff-only`. Os alunos não precisam compilar o portal; `UserData` embute o código no template base. Mudar arquivos em `app/` exige regenerar `01-base.yaml` e recriar a base (o `git pull` não atualiza EC2 já provisionada).
