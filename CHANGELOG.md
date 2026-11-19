\# Registro de Alterações — CRM SegSerra



Histórico das implementações, correções e ajustes realizados no sistema CRM em Python/Streamlit para a SegSerra (Bento Gonçalves/RS).



\---



\## \[18/11/2026] — Layout da Proposta, Itens em 4 Colunas e Aceite Comercial

\- \*\*O que foi feito:\*\*

&#x20; - Adicionado logotipo no cabeçalho da proposta comercial (usando `logo.png` quando disponível ou emblema institucional da SegSerra)\[cite: 1, 2].

&#x20; - Estruturado o escopo dos serviços em 4 colunas (\*\*Serviço\*\*, \*\*Valor unitário\*\*, \*\*Quantidade\*\* e \*\*Valor total\*\*) com cálculo automático (`quantidade \* valor\_unitario`) e soma no quadro de investimento.

&#x20; - Adicionada opção para adicionar ou remover linhas de serviços dinamicamente.

&#x20; - Implementado link de aceite comercial (`?proposta=<token>`) para visualização pelo cliente, opção de imprimir/salvar em PDF e confirmação dos termos alterando o status da proposta para \*\*Aprovada\*\*.

\- \*\*Arquivos envolvidos:\*\* `database.py`, `tela\_propostas.py`, `app.py`.

\- \*\*Motivo:\*\* Dar apresentação profissional para aprovação do cliente, permitir múltiplos serviços por proposta e agilizar o aceite sem burocracia excessiva\[cite: 1].



\---



\## \[18/11/2026] — Ajustes no Menu Lateral e Correção de Navegação

\- \*\*O que foi feito:\*\*

&#x20; - Removidos os prefixos numéricos das opções do menu lateral.

&#x20; - Movida a opção \*\*Usuários e Senhas\*\* para o final do menu, próxima ao botão de logout, e posicionadas as informações do usuário acima do logout.

&#x20; - Adicionada a opção para deixar o menu lateral fixo ou mais compacto.

&#x20; - Padronizado o redirecionamento do botão de lançar atividade no componente compartilhado.

\- \*\*Arquivos envolvidos:\*\* `app.py`, `utils.py`, `tela\_login.py`, `componentes.py`, `teste\_crm\_completo.py`\[cite: 1].

\- \*\*Motivo:\*\* Deixar a navegação mais limpa, dar controle do espaço lateral ao usuário e manter os testes automatizados alinhados com os nomes das telas\[cite: 1].



\---



\## \[18/11/2026] — Emissão de Propostas, Checklist de Visita Técnica e Testes Automatizados

\- \*\*O que foi feito:\*\*

&#x20; - Criado o módulo `tela\_propostas.py` com emissão de propostas no padrão da SegSerra, histórico no banco e exportação.

&#x20; - Criado o módulo `tela\_checklist.py` com itens de SST em `Sim`, `Não` e `Não aplicável`, contagem de pendências e histórico.

&#x20; - Criada a suíte de testes automatizados `teste\_crm\_completo.py` utilizando `unittest` e banco temporário isolado (`tempfile`).

&#x20; - Adicionada proteção contra tela em branco na inicialização do `app.py`.

\- \*\*Arquivos envolvidos:\*\* `database.py`, `tela\_propostas.py`, `tela\_checklist.py`, `app.py`, `teste\_crm\_completo.py`\[cite: 1].

\- \*\*Motivo:\*\* Cobrir o ciclo comercial e técnico de SST dentro do CRM e validar o funcionamento das rotinas sem alterar o banco de dados real\[cite: 1].



\---



\## \[18/11/2026] — Categorias de Clientes, CNAEs, Agenda e Resiliência na Consulta de CNPJ

\- \*\*O que foi feito:\*\*

&#x20; - Adicionado o campo \*\*Categoria\*\* (`Prospecto`, `Ativo`, `Mensalista`, `Inativo`) e captura/exibição de \*\*CNAE Principal\*\* e \*\*CNAEs Secundários\*\* no cadastro de clientes\[cite: 1].

&#x20; - Criado o módulo `tela\_agenda.py` com visão de follow-ups para hoje, atrasados, próximos 7 dias e banner de aviso no topo do sistema\[cite: 1].

&#x20; - Adicionado fallback automático na consulta de CNPJ em `utils.py` para contornar bloqueios temporários de limite (`Status 429`)\[cite: 1].

\- \*\*Arquivos envolvidos:\*\* `database.py`, `utils.py`, `componentes.py`, `tela\_clientes.py`, `tela\_agenda.py`, `app.py`\[cite: 1].

\- \*\*Motivo:\*\* Melhorar a segmentação de clientes, centralizar acompanhamentos comerciais e evitar falhas pontuais na consulta de CNPJ\[cite: 1].


## [19/11/2026] — Dashboard Inicial, Filtros de Propostas e Melhorias no Checklist
- **O que foi feito:**
  - Criado o módulo `tela_dashboard.py` como tela inicial após o login, exibindo propostas em aberto e follow-ups vencidos ou do dia.
  - Em `tela_propostas.py`, exibidas propostas em aberto no topo com filtro por status (em aberto, aceitas, recusadas ou todas) e ocultado o formulário de nova proposta até clicar no botão "Nova Proposta".
  - Em `tela_checklist.py` e `database.py`, adicionados campos de horário ("De" e "Até"), pessoas que acompanharam a visita e observações ocultas por grupo de itens (via `expander` recolhido).
- **Arquivos envolvidos:** `database.py`, `tela_dashboard.py`, `tela_propostas.py`, `tela_checklist.py`, `app.py`.
- **Motivo:** Facilitar a visão diária após o login, deixar a tela de propostas mais limpa e registrar horário, acompanhantes e observações por grupo na visita técnica.
## [19/11/2026] — Perfis de Usuário e Controle de Permissões por Acesso/Ação
- **O que foi feito:**
  - Adicionado o perfil **Técnico SST** além de **Administrador** e **Comercial / Atendimento**.
  - Criada a tabela `permissoes_perfil` no banco para controlar telas permitidas e permissões de **alterar** e **excluir** registros já emitidos.
  - Adicionada a aba **Permissões por Perfil** em `tela_login.py` e bloqueio de acesso/alteração/exclusão em `app.py` e `componentes.py`.
- **Arquivos envolvidos:** `database.py`, `tela_login.py`, `componentes.py`, `app.py`.
- **Motivo:** Restringir acesso a propostas e valores para usuários técnicos e controlar quem pode editar ou excluir registros emitidos.

## [19/11/2026] — Alteração de Propostas Não Aprovadas, Ações em Propostas Aprovadas e Permissões em Propostas
- **O que foi feito:**
  - Adicionado botão **Alterar Proposta** ao lado da seleção na tela de propostas, habilitado apenas quando o status não for **Aprovada** (e respeitando a permissão `pode_editar`).
  - Para propostas com status **Aprovada**, adicionadas as ações de **Cancelar Proposta** e **Duplicar p/ Nova Proposta** (preenchendo o formulário de nova proposta com base na proposta anterior).
  - Aplicada verificação de permissões (`pode_editar` e `pode_excluir`) na tela de propostas.
- **Arquivos envolvidos:** `database.py`, `tela_propostas.py`.
- **Motivo:** Proteger propostas já aprovadas contra edição direta, permitir duplicação ágil para novas emissões e reforçar o controle de acesso por perfil.

## [19/11/2026] — Correção ao Salvar Permissões e Ajustes no Dashboard
- **O que foi feito:**
  - Corrigido o salvamento de permissões por perfil em `tela_login.py` com atualização confiável do estado e aviso de confirmação.
  - Em `tela_dashboard.py`, ocultado o card de **Propostas em Aberto** para perfis que não sejam `Administrador` ou `Comercial / Atendimento`.
  - Adicionado card de **Checklists de Visita Técnica Emitidos** no dashboard com métricas e últimos registros.
- **Arquivos envolvidos:** `tela_login.py`, `tela_dashboard.py`.
- **Motivo:** Garantir que as permissões por perfil sejam gravadas corretamente, proteger informações comerciais no dashboard e dar visibilidade rápida aos checklists emitidos.

## [19/11/2026] — CEP Formatado com Busca Automática, Categoria Credenciada e Cadastro Rápido em Atividades
- **O que foi feito:**
  - Adicionada a categoria **Credenciada** em `CATEGORIAS_CLIENTE` (`database.py`).
  - Criadas funções de formatação e busca automática de CEP (`formatar_cep` e `consultar_cep_api`) em `utils.py`, mantendo preenchimento manual livre quando não localizado.
  - Removida a seção de **Posição do Funil** da tela de clientes e do modal de edição, e mantida apenas a relação de clientes cadastrados na consulta (`tela_clientes.py` e `componentes.py`).
  - Adicionada a opção de incluir um novo cliente diretamente na tela de lançamento de atividades (`tela_atividades.py`).
- **Arquivos envolvidos:** `database.py`, `utils.py`, `componentes.py`, `tela_clientes.py`, `tela_atividades.py`.
- **Motivo:** Facilitar o preenchimento de endereço com CEP, focar a gestão de clientes no cadastro, agilizar novos cadastros durante o lançamento de atividades e segmentar clínicas/parceiros credenciados.

## [19/11/2026] — Campo Status de Cliente, Separação de Busca CNPJ/CEP e Paginação na Lista
- **O que foi feito:**
  - Removidas as opções **Ativo** e **Inativo** da categoria de clientes e criado o campo **Status** (`Ativo` por padrão, ou `Inativo`) no banco, cadastro, filtros e modal de edição.
  - Desacoplada a busca de CEP da digitação automática e da busca de CNPJ: a busca por CEP agora ocorre apenas ao clicar em **Buscar CEP**, com preenchimento manual livre caso não encontre.
  - Aumentada a altura da listagem de clientes e adicionados contador de registros exibidos vs. total cadastrado e controle de páginas.
- **Arquivos envolvidos:** `database.py`, `componentes.py`, `tela_clientes.py`.
- **Motivo:** Separar classificação comercial de status operacional, evitar interferência entre consultas de CNPJ e CEP e facilitar a navegação em bases maiores de clientes.

## [19/11/2026] — Sincronização de Estado dos Campos no Cadastro de Clientes
- **O que foi feito:**
  - Atualizados diretamente os valores das chaves (`fld_*` e `input_cnpj_api`) no `st.session_state` ao clicar em **Limpar Campos**, **Buscar CNPJ** ou **Buscar CEP** em `tela_clientes.py`.
- **Arquivos envolvidos:** `tela_clientes.py`.
- **Motivo:** Garantir que os botões de limpar e consultar CNPJ reflitam imediatamente nos campos da tela do Streamlit.

## [19/11/2026] — Desmarcação Automática na Tabela de Clientes e Aviso Temporário na Alteração
- **O que foi feito:**
  - Adicionado controle de chave da tabela (`tabela_clientes_nonce`) e callback `on_dismiss` no modal de edição para desmarcar automaticamente a linha ao fechar, salvar ou excluir, retornando à tela de consulta com mensagem temporária.
  - Garantida a sincronização do campo `fld_email` ao consultar dados pelo CNPJ.
- **Arquivos envolvidos:** `componentes.py`, `tela_clientes.py`.
- **Motivo:** Evitar que o modal reabra sozinho após fechar ou salvar e tornar o retorno para a consulta de clientes mais limpo.

## [19/11/2026] — Preenchimento de Responsável via QSA e Ajuste de E-mail na Busca por CNPJ
- **O que foi feito:**
  - Adicionado preenchimento automático do campo **Responsável** (`fld_resp`) com os nomes do quadro societário (`qsa`) separados por `" / "` quando disponíveis na consulta de CNPJ.
  - Reforçada a leitura de e-mail da API e removido o `sleep` bloqueante durante a exibição de mensagens na tela de clientes.
- **Arquivos envolvidos:** `tela_clientes.py`.
- **Motivo:** Aproveitar os sócios/administradores retornados na consulta de CNPJ e manter a interface fluida.

## [19/11/2026] — Padronização de Propostas, Foco ao Criar e Dados do Cliente
- **O que foi feito:**
  - Estruturada a tela de propostas com tabela interativa de propostas emitidas, seleção de linha e botão **Nova Proposta** no topo, seguindo o padrão de consulta/cadastro de clientes.
  - Adicionado foco automático no primeiro campo ao abrir o formulário de nova proposta.
  - Configurado o preenchimento automático de **Solicitante** e **Contatos** com o **Responsável**, **Telefone** e **E-mail** cadastrados no cliente selecionado.
- **Arquivos envolvidos:** `tela_propostas.py`.
- **Motivo:** Deixar a navegação de propostas mais intuitiva e evitar redigitação de dados já cadastrados do cliente.

## [19/11/2026] — Simplificação da Tela de Propostas com Abertura Direta na Seleção
- **O que foi feito:**
  - Simplificada `tela_propostas.py` para exibir o quadro de propostas emitidas com filtros acima e o botão **Nova Proposta**, abrindo diretamente a tela de emissão ou edição ao clicar em **Nova Proposta** ou selecionar uma proposta na tabela.
- **Arquivos envolvidos:** `tela_propostas.py`.
- **Motivo:** Deixar a navegação mais direta e menos carregada de controles intermediários.

## [19/11/2026] — Pré-visualização ao Selecionar Proposta para Alteração
- **O que foi feito:**
  - Exibida a pré-visualização da proposta (documento formatado e texto simples) também ao selecionar uma proposta para alteração ou consulta em `tela_propostas.py`.
- **Arquivos envolvidos:** `tela_propostas.py`.
- **Motivo:** Permitir conferir o documento completo antes e durante a edição da proposta, no mesmo padrão da emissão de nova proposta.

## [19/11/2026] — Melhorias no Checklist: Lista com Filtros, Validação de Horário e Itens Ocultos
- **O que foi feito:**
  - Exibidos inicialmente os checklists já emitidos com filtros por empresa, responsável técnico e pendências, além do botão **Novo Checklist**.
  - Adicionada validação para impedir que o horário final ("Até") seja menor ou igual ao horário inicial ("De").
  - Mantidos os itens de verificação em campo ocultos até o usuário clicar em **Adicionar Itens de Verificação**.
- **Arquivos envolvidos:** `tela_checklist.py`.
- **Motivo:** Padronizar a navegação com as demais telas, evitar registros com intervalo de horário inválido e deixar o formulário inicial mais limpo.

## [19/11/2026] — Seleção Direta na Tabela de Checklists e Foco Automático ao Criar
- **O que foi feito:**
  - Removida a seleção em lista (`selectbox`) abaixo da tabela de checklists emitidos em `tela_checklist.py` e habilitada a seleção direta por clique na linha do quadro.
  - Adicionado foco automático no primeiro campo (**Empresa / Cliente**) ao clicar em **Novo Checklist**.
- **Arquivos envolvidos:** `tela_checklist.py`.
- **Motivo:** Padronizar a seleção de documentos pelo quadro e agilizar o início do preenchimento de novos checklists.

## [19/11/2026] — Correção de StreamlitWidgetAlreadyInstantiatedError na Navegação do Dashboard
- **O que foi feito:**
  - Alterado `_navegar_para_tela` em `tela_dashboard.py` para gravar `navegar_para_pendente` e aplicada a atualização de `menu_pagina` em `app.py` antes da instanciação do `st.radio`.
- **Arquivos envolvidos:** `app.py`, `tela_dashboard.py`.
- **Motivo:** Respeitar o ciclo de vida dos widgets do Streamlit ao navegar pelos atalhos do dashboard.

## [19/11/2026] — Navegação do Dashboard via Callback e Chave Independente no Radio
- **O que foi feito:**
  - Alterados os botões do dashboard para usarem `on_click` com `_solicitar_navegacao` e desvinculada a chave `radio_menu_pagina` em `app.py` via `pagina_ativa` com `index=idx_pagina`.
- **Arquivos envolvidos:** `app.py`, `tela_dashboard.py`.
- **Motivo:** Evitar `StreamlitWidgetAlreadyInstantiatedError` ao acionar atalhos de navegação do dashboard.

