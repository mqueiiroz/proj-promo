# Guia das colunas do painel

## Gestão de ofertas

| Coluna | O que fica salvo e de onde vem | Para que serve e exemplo |
| --- | --- | --- |
| **Produto** | O nome coletado fica em `PRODUTO.NOME`. | Identifica o item. Exemplo **Processador AMD Ryzen 5 5600XT**. |
| **Loja** | A loja fica vinculada ao produto por `PRODUTO.LOJA_ID`. O nome vem de `LOJA.NOME`. | Mostra onde o item foi encontrado. Exemplo **Kabum**. |
| **Fonte** | **Coleta local** é um texto fixo do painel. O Oracle guarda os dados coletados pelo Python. | Indica de onde vieram os dados. **Coleta local** significa que o coletor roda no computador, lê os dados da loja e grava no Oracle. O rótulo aparece tanto em produtos recém-cadastrados quanto nos que já existiam. |
| **Cadastrado em** | A data e a hora do primeiro cadastro ficam em `PRODUTO.CRIADO_EM`. | Mostra quando o produto entrou no sistema. Se foi cadastrado às **10h** e lido novamente às **10h15**, esta coluna continua mostrando **10h**. |
| **Promoção desde** | A data e a hora ficam em `PRODUTO.PROMOCAO_DESDE`. O coletor registra quando confirma uma promoção com preço e atualiza a data se o preço promocional cair ou a oferta voltar. | Mostra quando o coletor detectou a oferta ou a queda mais recente do preço promocional. Se o produto entrou em promoção às **11h** e ficou mais barato às **11h30**, a coluna passa a mostrar **11h30**. O traço **—** aparece quando a oferta está inativa ou a data ainda está vazia, como em uma oferta antiga que ainda não foi confirmada após a criação da coluna. |
| **Última coleta** | A data e a hora da última leitura bem-sucedida ficam em `PRODUTO.VISTO_EM`. | Mostra quão recente é a informação. Se o Ryzen foi lido às **11h45** pelo mesmo preço, a coluna muda para **11h45** e o histórico de preços mantém os mesmos pontos. |
| **Status** | O painel calcula o valor com a situação da loja, a disponibilidade do produto e a comparação entre o preço original e o atual. | **Ativa** indica uma oferta disponível em loja ativa com desconto. **Sem desconto** indica um produto disponível em loja ativa sem desconto identificado. **Indisponível** indica um produto indisponível ou uma loja inativa. |
| **Ação** | O link **Ver detalhes** é montado com o ID salvo em `PRODUTO.ID`. | Abre a página do item, onde é possível ver seu histórico de preços. Exemplo `/produto.html?id=64`. |

## Últimos eventos

| Coluna | O que fica salvo e de onde vem | Para que serve e exemplo |
| --- | --- | --- |
| **Data e hora** | O momento em que o evento foi registrado fica em `LOG_COLETA.CRIADO_EM`. | Indica quando aconteceu o evento daquela linha. Exemplo **18/11/2026 às 15h41**. |
| **Loja** | O evento guarda `LOG_COLETA.LOJA_ID`. O nome vem de `LOJA.NOME`. | Identifica a loja relacionada ao evento. Exemplo **Kabum**. |
| **Evento** | O tipo fica em `LOG_COLETA.TIPO`. O painel exibe um rótulo para cada código. | Mostra o que aconteceu. Exemplo **Produto novo** indica que o coletor cadastrou aquele item pela primeira vez. |
| **Produto** | Quando há vínculo com um item, o evento guarda `LOG_COLETA.PRODUTO_ID`. O nome exibido vem do cadastro do produto. | Identifica o item afetado. Uma **Coleta concluída** vinculada ao Ryzen mostra o nome dele. Um resumo de categoria ou da rodada inteira aparece com **—** porque o evento abrange vários itens. |

### O que significa cada evento

| Evento | O que indica | Exemplo |
| --- | --- | --- |
| **Coleta concluída** | Uma leitura de produto ou uma execução de coleta terminou com sucesso. | O coletor releu o Ryzen e salvou o resultado com o nome do produto, mesmo com o preço igual. O resumo da categoria CPU também pode gerar esse evento. |
| **Produto novo** | O coletor criou o primeiro cadastro daquele produto no sistema. | O Ryzen apareceu pela primeira vez e ganhou um cadastro no Oracle. |
| **Preço alterado** | O preço atual coletado mudou em relação ao preço salvo. | O preço passou de **R$ 1.059,99** para **R$ 999,99** e a queda entrou no histórico. |
| **Produto esgotado** | O produto passou de disponível para indisponível. | A loja informou falta de estoque ou a coleta confirmou a remoção da página. |
| **Voltou ao estoque** | Um produto que estava indisponível voltou a ficar disponível. | O coletor encontrou novamente o Ryzen à venda. |
| **Falha na coleta** | Ocorreu uma falha na leitura ou na gravação dos dados. | Uma página deu erro durante a coleta. Os dados anteriores são preservados nas operações que falharam. |

## Exemplo de uma sequência

1. **10h**. O coletor cadastra o Ryzen por **R$ 1.059,99**. A fonte é **Coleta local**, aparece o evento **Produto novo** e o primeiro preço entra no histórico.
2. **10h15**. O coletor lê o mesmo preço. **Última coleta** passa para **10h15**, aparece **Coleta concluída** com o nome do produto e o histórico mantém um ponto.
3. **10h30**. O preço cai para **R$ 999,99** e fica abaixo do preço original. **Promoção desde** passa para **10h30**, aparece **Preço alterado** e o novo valor entra no histórico.
