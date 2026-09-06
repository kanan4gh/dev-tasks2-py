# vendor

ここに置いてあるファイルは、外部から取得してそのままリポジトリに含めたものである。

| ファイル | 取得元 | SHA-256 |
|---|---|---|
| `react.production.min.js` | https://unpkg.com/react@18.3.1/umd/react.production.min.js | `d949f1c3687aedadcedac85261865f29b17cd273997e7f6b2bfc53b2f9d4c4dd` |
| `react-dom.production.min.js` | https://unpkg.com/react-dom@18.3.1/umd/react-dom.production.min.js | `35f4f974f4b2bcd44da73963347f8952e341f83909e4498227d4e26b98f66f0d` |
| `htm.umd.js` | https://unpkg.com/htm@3.1.1/dist/htm.umd.js | `7a31776e04bd4afde0d4308177d26f377716fcf7e4bd70be590746d6aa594f08` |

取得日: 2026-09-07

## なぜ同梱するのか

- **実行時に CDN を読まない。** ローカル専用のツールが、画面を開くたびに外部へ
  通信するのを避ける。オフラインでも壊れない
- **ビルド工程を持ち込まない。** node / npm をこのリポジトリに入れない方針のため、
  バンドラで固める代わりに UMD ビルドをそのまま置く。JSX の代わりに
  [htm](https://github.com/developit/htm) のタグ付きテンプレートリテラルを使う

いずれも UMD なのでグローバル（`window.React` / `window.ReactDOM` / `window.htm`）に
載る。自前のコードは `../js/` の ES モジュールからそれを参照する。

## 更新のしかた

上の URL のバージョン部分を変えて取得し直し、この表のバージョンと SHA-256 を
更新する。`shasum -a 256 <file>` で計算できる。
