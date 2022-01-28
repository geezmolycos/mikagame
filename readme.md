# mika 游戏及游戏库

这里是名为mika的游戏及游戏库，游戏使用python语言编写，目前还没有开始开发本体。

游戏库实现了类curses的字符界面显示，后端采用python写成，使用Pyodide运行在浏览器中。

游戏库提供了一种类tex语法的标记语言，可以方便地描述字符风格、动画、位置等内容。

```plaintext
\tick[$0.1]Behold\delay[$0.5], here I am!\delay[$1.0]
The {\[bg=gray]Most {\[fg=gold]\tick[$0.4]ALMIGHTY} and {\[fg=red]\tick[$0.4]POWERFUL}}
{\[bg=red]Dragon} in this Kingdom!
```
