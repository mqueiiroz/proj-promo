<?php
declare(strict_types=1);

// Adaptador exclusivo do CT-01. É copiado para a aplicação temporária do teste.
final class BancoCt01 extends PDO
{
    public function prepare(string $query, array $options = []): PDOStatement|false
    {
        return parent::prepare($this->sqlCompativel($query), $options);
    }

    public function query(string $query, ?int $fetchMode = null, mixed ...$fetchModeArgs): PDOStatement|false
    {
        return parent::query($this->sqlCompativel($query), $fetchMode, ...$fetchModeArgs);
    }

    private function sqlCompativel(string $sql): string
    {
        $sql = preg_replace('/OFFSET ([0-9]+) ROWS FETCH NEXT ([0-9]+) ROWS ONLY$/i', 'LIMIT $2 OFFSET $1', $sql);
        return preg_replace('/FETCH FIRST ([0-9]+) ROWS ONLY$/i', 'LIMIT $1', $sql);
    }
}

function conectarBanco(): PDO
{
    $arquivo = dirname(__DIR__) . '/ct01.sqlite';
    if (!is_file($arquivo)) {
        throw new RuntimeException('Banco de teste ausente.');
    }
    $banco = new BancoCt01('sqlite:' . $arquivo, options: [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_CASE => PDO::CASE_UPPER,
    ]);
    $banco->sqliteCreateFunction('TO_CHAR', static function (?string $data, string $formato): ?string {
        if ($data === null) {
            return null;
        }
        $mascara = match ($formato) {
            'YYYY-MM-DD HH24:MI:SS' => 'Y-m-d H:i:s',
            'DD/MM/YYYY HH24:MI:SS' => 'd/m/Y H:i:s',
        };
        return (new DateTimeImmutable($data))->format($mascara);
    }, 2);
    return $banco;
}
