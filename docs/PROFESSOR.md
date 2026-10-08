# Preparação do professor

## Decisão essencial

O projeto contempla os sete serviços, mas a compatibilidade com o laboratório da turma ainda precisa ser comprovada. Não prometa executar o percurso completo apenas porque esses serviços aparecem na ementa. Academy pode restringir operações específicas, tipos EC2, regiões e cotas. Não há tentativa de contornar essas restrições neste projeto.

**Critério para liberar a aula completa:** um ensaio de criação, atualização, testes e exclusão dos seis templates na mesma modalidade de laboratório usada pelos alunos. Uma chamada de listagem ou `validate-template` não comprova permissão para criar recursos. Se Route 53, ACM ou WAF forem negados, solicite ao responsável pelo curso um ambiente autorizado compatível; não apresente uma simulação como uso real do serviço.

## Domínio e preparação anterior à aula

Para cada grupo executar o conjunto completo em sua própria conta:

1. Providencie um domínio público sob controle do professor/instituição. Não é necessário comprar um domínio por aluno nem registrá-lo no Academy.
2. Reserve um subdomínio exclusivo por grupo, por exemplo `grupo01.lab.seudominio.edu.br`.
3. Em cada conta, crie a stack `03-dns-publico.yaml`. Anote os quatro NS e o PublicZoneId.
4. No DNS autoritativo do pai, publique a delegação NS para o nome completo atribuído ao grupo. A zona pai precisa ser autoritativa: se `lab.seudominio.edu.br` não é uma zona separada, a delegação pode ser criada na zona `seudominio.edu.br` com o nome `grupo01.lab`.
5. Confirme a resolução pública e só então crie a stack `04-certificado.yaml` naquela conta/região.
6. Aguarde ACM ISSUED. Não deixe a emissão/propagação para a aula de 90 minutos.
7. Entregue ao grupo o PortalHostname, PublicZoneId e CertificateArn. Eles não são senhas. O aluno irá inspecionar esses recursos e criar o listener HTTPS/A Alias na aula.

O certificado precisa existir na conta e região do ALB de cada grupo; não reutilize diretamente um ARN de outra conta. Se nenhum domínio estiver disponível, a parte HTTP/DNS privado/WAF ainda é útil, mas o objetivo de HTTPS público com ACM não fica completo. ACM Private CA não é usado como atalho: acrescentaria serviço, custo e distribuição de confiança.

Uma opção pedagógica é preparar DNS/ACM em uma sessão anterior de 15–30 minutos mais a espera pela propagação. A aula de 90 minutos passa a aproveitar esses recursos já válidos. Se todos precisarem criar tudo do zero durante a mesma sessão, amplie o tempo ou divida o laboratório em dois encontros.

## Ensaio obrigatório

- [ ] Modalidade do Academy e restrições identificadas; região definida.
- [ ] Tipo EC2 permitido (duas instâncias por grupo) e duas AZs disponíveis.
- [ ] AMI oficial AL2023 **standard x86_64** validada, com `/usr/bin/python3`, cloud-init, tar e systemd. Não use minimal ou imagem de container.
- [ ] Criação da base e dois targets healthy. Cronometrar: ______.
- [ ] Página abre e as duas instâncias respondem ao ALB.
- [ ] Teste de parada/retorno de uma instância executado.
- [ ] DNS privado retorna IPs de dentro da VPC.
- [ ] Delegação pública e certificado ISSUED em cada conta.
- [ ] HTTPS válido, A Alias correto e redirecionamento HTTP testado.
- [ ] WAF Count → Block resulta em 200 → 403 para `/admin`.
- [ ] Desativação da regra/exclusão limpa funciona.
- [ ] Todas as stacks excluídas no ensaio; CNAME ACM residual tratado; delegação removida antes de liberar a zona.
- [ ] Saldo/cotas suficientes. Guardar o tempo de exclusão: ______.

O projeto não cria roles IAM e não usa instance profile. A sessão do CloudFormation continua precisando das permissões de EC2/VPC, ELBv2, Route 53, ACM, WAFv2 e CloudFormation. Mantenha as políticas do laboratório intactas.

## Aula de 90 minutos

DNS público e certificado já preparados. Alunos em duplas, idealmente um ambiente por dupla conforme regras da turma. Se cada aluno tiver conta própria, ele cria os recursos apenas na sua conta; não compartilhe credenciais.

| Minutos | Atividade |
|---|---|
| 0–15 | Conceitos e caminho da requisição: VPC, SG, ALB, DNS, TLS, WAF e IaC. |
| 15–25 | Abrir repositório, revisar template, preencher parâmetros e iniciar base. |
| 25–35 | Enquanto provisiona, explicar CIDR/rotas, inbound/outbound e camadas. |
| 35–45 | Portal, targets e inspeção de isolamento. |
| 45–53 | Parar uma EC2, observar continuidade, reiniciar. |
| 53–61 | Criar zona privada e testar DNS pelo portal. |
| 61–72 | Inspecionar DNS/ACM preparados; criar HTTPS/A Alias e redirecionamento. |
| 72–80 | WAF Count/Block, comparação 200/403 e evidências. |
| 80–90 | Excluir extensões e base; acompanhar eventos e conferir recursos. |

Esse cronograma é uma meta a confirmar no ensaio: provisão/exclusão da AWS não tem prazo fixo. Inicie a limpeza mais cedo se a turma atrasar e mantenha acompanhamento após o horário se houver DELETE_IN_PROGRESS/DELETE_FAILED. Tenha um ambiente de demonstração previamente validado para explicar enquanto a turma aguarda; ele também deve ser removido.

## Custos e uso temporário

Há custos potenciais de duas EC2, dois volumes gp3, ALB (tempo + capacidade), endereços IPv4 públicos do ALB, duas hosted zones e WAF (Web ACL, regra e requisições). O certificado público não exportável integrado ao ALB segue a política de preços atual do ACM; confira a página oficial antes do ensaio. Não usamos Private CA, regras de Marketplace ou Bot Control.

Não estimamos o valor total sem região, duração real e quantidade de grupos. Preencha essa conta no AWS Pricing Calculator antes da aula. **Não suponha que toda cobrança é proporcional aos minutos de uso**: hosted zones possuem regras próprias de cobrança mensal. WAF tem componentes por tempo e por requisição. Créditos Academy não tornam recursos gratuitos.

Use uma Web ACL com uma regra, ative somente durante o exercício e exclua depois. Não execute carga intensa. Desligar as EC2 ou encerrar a sessão do Academy não substitui a exclusão dos recursos. Consulte links em FONTES.md.

## O que foi simplificado

- Portal somente leitura; sem autenticação, inscrições, banco ou dados pessoais.
- Sem Auto Scaling: o ALB distribui tráfego, mas não cria servidores.
- Duas camadas de infraestrutura: entrada e aplicação. Não há camada de banco.
- HTTP entre ALB e EC2, HTTPS apenas até ALB.
- Sem SSH/SSM/NAT: bootstrap vem do UserData e os logs iniciais aparecem no console EC2. Isso é uma escolha para o laboratório, não recomendação universal de operação.
- SG da aplicação não tem saída geral. Respostas permitidas funcionam por stateful; AmazonProvidedDNS não é filtrado por SG.
- WAF bloqueia um caminho fictício. Não se afirma proteção completa contra SQL injection, XSS ou todas as ameaças.
- Stacks separadas recebem IDs por parâmetros, sem exports cruzados. Por isso o aluno deve respeitar a ordem de exclusão mesmo que CloudFormation não impeça todos os erros entre stacks.
- `CREATE_COMPLETE` não atesta prontidão do portal: validar target group e HTTP é obrigatório.

## Publicar o repositório

O pacote está pronto para Git, mas **não foi publicado remotamente**. Use um repositório novo vazio, criado na conta/organização correta, com visibilidade escolhida pelo responsável. Não envie credenciais, IDs de acesso temporários, arquivos `.aws/`, chaves ou segredos.

Na pasta extraída:

```bash
git init -b main
git add .
git commit -m "Adiciona laboratorio Campus na Nuvem"
git remote add origin URL_DO_REPOSITORIO_VAZIO
git push -u origin main
```

Se Git solicitar identidade, configure com os dados do responsável. Não sobrescreva um repositório existente. Compartilhe com os alunos a URL real e ajuste o exemplo de clone no README. Primeira obtenção é `git clone`; `git pull --ff-only` serve para atualizar uma cópia já clonada.

## Evolução futura

Depois do ensaio, registre parâmetros realmente aceitos no Academy e os tempos observados. O material teórico/slides será construído em outra etapa, usando os resultados deste laboratório. O roteiro de vídeo disponível aqui é um apoio para gravar a demonstração prática, não um vídeo já publicado.
