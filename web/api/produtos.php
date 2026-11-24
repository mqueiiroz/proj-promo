<?php
declare(strict_types=1);

require_once dirname(__DIR__, 2) . '/app/api.php';
if (!prepararApiGet()) {
    return;
}
require dirname(__DIR__, 2) . '/app/banco.php';
$categoria = $_GET['categoria'] ?? '';
if (!in_array($categoria, ['', 'GPU', 'SSD', 'RAM', 'CPU', 'FONTE', 'COOLER', 'WATER_COOLER', 'GABINETE', 'HD', 'PLACA_MAE'], true)) {
    http_response_code(400);
    echo json_encode(['erro' => 'Categoria inválida.'], JSON_UNESCAPED_UNICODE);
    return;
}

try {
    $banco = conectarBanco();
    $consulta = $banco->prepare(
        'SELECT v.ID, v.NOME, v.LOJA, v.CATEGORIA, v.PRECO_ATUAL, v.PRECO_ORIGINAL, v.DESCONTO_PCT, '
        . 'p.URL_ORIGINAL, v.URL_AFILIADO '
        . 'FROM V_PROMOCOES_ATIVAS v JOIN PRODUTO p ON p.ID = v.ID '
        . 'JOIN LOJA l ON l.ID = p.LOJA_ID WHERE l.ATIVA = 1 '
        . ($categoria === '' ? '' : 'AND v.CATEGORIA = :categoria ')
        . 'ORDER BY v.DESCONTO_PCT DESC, p.ATUALIZADO_EM DESC, p.ID DESC'
    );
    $consulta->execute($categoria === '' ? [] : ['categoria' => $categoria]);
    $produtos = [];
    foreach ($consulta as $linha) {
        $produtos[] = [
            'id' => (string) $linha['ID'],
            'nome' => $linha['NOME'], 'loja' => $linha['LOJA'], 'categoria' => $linha['CATEGORIA'],
            // Texto decimal preserva os centavos no transporte JSON.
            'preco' => $linha['PRECO_ATUAL'] === null ? null : (string) $linha['PRECO_ATUAL'],
            'preco_original' => (string) $linha['PRECO_ORIGINAL'],
            'desconto_pct' => (int) $linha['DESCONTO_PCT'],
            'disponivel' => true, 'url' => $linha['URL_ORIGINAL'],
            'url_afiliado' => $linha['URL_AFILIADO'],
        ];
    }
    echo json_encode(['produtos' => $produtos], JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR);
} catch (Throwable $erro) {
    http_response_code(503);
    echo json_encode(['erro' => 'Não foi possível carregar os produtos. Tente novamente mais tarde.'], JSON_UNESCAPED_UNICODE);
}
