
# LightClip v1.3 - 多主題剪貼簿工具（VS Code / EXE 支援）

本專案為 Python 3.13 + PyQt5 撰寫的輕量剪貼簿工具，特色：

- 剪貼簿歷史：自動記錄文字 / 圖片 / 網址 / 檔案路徑
- 模板系統：常用句子、簽名、客服回覆、可綁定快捷鍵 1~9
- 多主題：6 組深色 / 淺色 / 科技感 / 奶油系主題
- 多語系：繁體中文 / English
- 大字版 UI：預設 18px，適合長時間閱讀
- JSON 儲存：完全本機，不連網
- 系統托盤：可縮小於托盤，熱鍵呼叫
- 全域快捷鍵：Ctrl+Shift+C 叫出視窗，Ctrl+Shift+1~9 貼上模板
- VS Code 友善：適合編輯 / 除錯 / 打包 EXE

## 安裝相依套件

```bash
pip install -r requirements.txt
```

## 在 VS Code 執行

1. 用 VS Code 開啟資料夾 `LightClip_v1_3`
2. 選擇 Python 3.13 直譯器
3. 執行：

```bash
python main.py
```

## 打包為 EXE

```bash
build_exe.bat
```

完成後可在 `dist/LightClip/LightClip.exe` 找到執行檔。

若要建立安裝程式，請使用 `build_installer.iss` 搭配 Inno Setup Compiler。
