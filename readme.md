# mika 游戏及游戏库

这里是名为mika的游戏及游戏库，游戏使用python语言编写，目前还没有开始开发本体。

游戏库实现了类curses的字符界面显示，后端采用python写成，使用Pyodide运行在浏览器中。

游戏库提供了一种类tex语法的标记语言，可以方便地描述字符风格、动画、位置等内容。

```plaintext
\tick[:0.1]Behold\delay[:0.5], here I am!\delay[:1.0]
The {\s[bg=gray]Most {\s[fg=gold]\tick[:0.4]ALMIGHTY} and {\s[fg=red]\tick[:0.4]POWERFUL}}
{\s[bg=red]Dragon} in this Kingdom!
```

## TODO

- [x] 地图显示系统
  - 采用选项的方式实现，其实就是对话系统！
  - 地图包括许多场景，每个场景代表一个地点。
  - 每个场景有场景描述。从每个场景，可以去往其他场景（有去其他场景的选项），还可以和场景中的人物对话（也是选项）
  - 人物对话时，场景不能操作，需要到对话结束后方可操作。
  - 每个人物都有一个id，在地图场景的\ts命令，设置一个参数，是dialogue，该参数比to参数优先，触发人物对话
  - 在人物对话触发后，地图会重新渲染，此时，/st参数中的character_dialogue_m会被设成True，否则被设成False
