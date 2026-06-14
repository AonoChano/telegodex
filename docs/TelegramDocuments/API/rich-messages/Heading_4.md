# Heading 4

##### Heading 5
###### Heading 6

Paragraph text

```python
  print(&#39;pre-formatted fixed-width code block written in the Python programming language&#39;)
```

---

- unordered list item
* unordered list item
+ unordered list item

1. ordered list item
2. ordered list item

- [ ] task list item
- [x] completed task list item

&gt;Block quotation started
&gt;
&gt;Block quotation continued on the next line
&gt;Block quotation continued on the same line
&gt;
&gt;The last line of the block quotation

![](https://telegram.org/example/photo.jpg)
![](https://telegram.org/example/video.mp4)
![](https://telegram.org/example/audio.mp3)
![](https://telegram.org/example/audio.ogg)
![](https://telegram.org/example/animation.gif)

![](https://telegram.org/example/photo.jpg &quot;Photo caption&quot;)
![](https://telegram.org/example/video.mp4 &quot;Video caption&quot;)
![](https://telegram.org/example/audio.mp3 &quot;Audio caption&quot;)
![](https://telegram.org/example/audio.ogg &quot;Voice note caption&quot;)
![](https://telegram.org/example/animation.gif &quot;Animation caption&quot;)

| Header 1 | Header 2 |
|:---------|:--------:|
| left     | center   |

Text with a reference[^id1] and another one[^id2].

[^id1]: Definition of the first footnote.
[^id2]: Definition of the second footnote.

$$E = mc^2$$

```math
E = mc^2
```

## Example Nested Syntax Report for _Q1_
Intro with &lt;u&gt;underlined text&lt;/u&gt;, ==marked text==, and $x^2 + y^2$.
**Bold _italic &lt;u&gt;underlined italic bold&lt;/u&gt; italic_ bold**
&lt;u&gt;In inline tags, nested **markdown** is parsed&lt;/u&gt;
&gt;Quote with **bold text, ~~strikethrough, and &lt;tg-spoiler&gt;spoiler&lt;/tg-spoiler&gt;~~**, plus [a link](https://t.me/).

- List item with `code`, &lt;sup&gt;superscript&lt;/sup&gt;, &lt;sub&gt;subscript&lt;/sub&gt;, and a footnote[^note]
- Another item with **bold &lt;tg-spoiler&gt;&lt;code&gt;spoiler code&lt;/code&gt;&lt;/tg-spoiler&gt;**
- Another item with ~~strikethrough and &lt;ins&gt;inserted text&lt;/ins&gt;~~

| Metric | Value |
|:-------|------:|
| Speed  | **42** &lt;sup&gt;ms&lt;/sup&gt; |
| Status | &lt;tg-spoiler&gt;ready&lt;/tg-spoiler&gt; |

[^note]: Footnote with _italic text_ and &lt;u&gt;HTML underline&lt;/u&gt;.

---

# Details blocks can contain Markdown content:

&lt;details open&gt;&lt;summary&gt;Summary with **bold text**&lt;/summary&gt;

### Details heading
- List item with _italic text_
- List item with &lt;tg-spoiler&gt;spoiler&lt;/tg-spoiler&gt;

&lt;/details&gt;

# Collages and slideshows can contain Markdown media blocks:

&lt;tg-collage&gt;

![](https://telegram.org/example/photo.jpg)
![](https://telegram.org/example/video.mp4)

&lt;/tg-collage&gt;

&lt;tg-slideshow&gt;

![](https://telegram.org/example/photo.jpg)
![](https://telegram.org/example/video.mp4)

&lt;/tg-slideshow&gt;</code></pre>
<p>For formatting features that don&#39;t have Markdown syntax, use <a href="#rich-html-style">HTML tags</a>:</p>
<pre><code>&lt;u&gt;underlined text&lt;/u&gt;, &lt;ins&gt;underlined text&lt;/ins&gt;
&lt;sub&gt;subscript text&lt;/sub&gt;
&lt;sup&gt;superscript text&lt;/sup&gt;
&lt;a name=&quot;chapter-1&quot;&gt;&lt;/a&gt;
&lt;aside&gt;Pull quote&lt;cite&gt;The Author&lt;/cite&gt;&lt;/aside&gt;
&lt;details open&gt;&lt;summary&gt;Title&lt;/summary&gt;Content&lt;/details&gt;
&lt;tg-map lat=&quot;41.9&quot; long=&quot;12.5&quot; zoom=&quot;14&quot;/&gt;
&lt;tg-collage&gt;&lt;img src=&quot;https://telegram.org/example/photo.jpg&quot;/&gt;&lt;figcaption&gt;Caption&lt;cite&gt;The Author&lt;/cite&gt;&lt;/figcaption&gt;&lt;/tg-collage&gt;
&lt;tg-slideshow&gt;&lt;img src=&quot;https://telegram.org/example/photo.jpg&quot;/&gt;&lt;video src=&quot;https://telegram.org/example/video.mp4&quot;/&gt;&lt;figcaption&gt;Slideshow caption&lt;cite&gt;The Author&lt;/cite&gt;&lt;/figcaption&gt;&lt;/tg-slideshow&gt;</code></pre>
<p>Please note:</p>
<ul>
<li>Rich Markdown is compatible with GitHub Flavored Markdown where possible and can contain arbitrary HTML. Supported rich message HTML tags are parsed as described in <a href="#rich-html-style">Rich HTML style</a>.</li>
<li>Media can be specified only as a separate block.</li>
<li>Media blocks support only HTTP and HTTPS URLs.</li>
<li>Media type is determined by the MIME type and the URL of the media.</li>
<li>In media syntax, the optional title after the URL is used as the caption; for example, <img class="icon" src="url" alt="" title="Photo caption"> displays “Photo caption” under the media.</li>
<li>Table cells can contain only inline formatting.</li>
<li>Formula source is treated as raw LaTeX.</li>
<li>See <a href="#date-time-entity-formatting">date-time entity formatting</a> for more details about supported date-time formats.</li>
</ul>
<h6><a class="anchor" name="rich-html-style" href="#rich-html-style"><i class="anchor-icon"></i></a>Rich HTML style</h6>
<p>To use this mode, pass rich message content in the <em>html</em> field. The following tags are currently supported:</p>
<pre><code>&lt;a name=&quot;chapter-0&quot;&gt;&lt;/a&gt;
&lt;b&gt;bold text&lt;/b&gt;, &lt;strong&gt;bold text&lt;/strong&gt;
&lt;i&gt;italic text&lt;/i&gt;, &lt;em&gt;italic text&lt;/em&gt;
&lt;u&gt;underlined text&lt;/u&gt;, &lt;ins&gt;underlined text&lt;/ins&gt;
&lt;s&gt;strikethrough text&lt;/s&gt;, &lt;strike&gt;strikethrough text&lt;/strike&gt;, &lt;del&gt;strikethrough text&lt;/del&gt;
&lt;code&gt;inline fixed-width code&lt;/code&gt;
&lt;mark&gt;marked text&lt;/mark&gt;
&lt;sub&gt;subscript text&lt;/sub&gt;
&lt;sup&gt;superscript text&lt;/sup&gt;
&lt;tg-spoiler&gt;spoiler&lt;/tg-spoiler&gt;

&lt;a href=&quot;#note-1&quot;&gt;Reference&lt;/a&gt;
&lt;a href=&quot;https://t.me/&quot;&gt;inline URL&lt;/a&gt;
&lt;a href=&quot;mailto:user@example.com&quot;&gt;inline e-mail&lt;/a&gt;
&lt;a href=&quot;tel:+123456789&quot;&gt;inline phone number&lt;/a&gt;
&lt;a href=&quot;tg://user?id=123456789&quot;&gt;inline mention of a user&lt;/a&gt;
&lt;a href=&quot;#chapter-1&quot;&gt;in-document link&lt;/a&gt;
&lt;a name=&quot;chapter-1&quot;&gt;&lt;/a&gt;

&lt;tg-reference name=&quot;note-1&quot;&gt;Referenced text&lt;/tg-reference&gt;
&lt;tg-emoji emoji-id=&quot;5368324170671202286&quot;&gt;<img class="emoji" src="//telegram.org/img/emoji/40/F09F918D.png" width="20" height="20" alt="👍" />&lt;/tg-emoji&gt;
&lt;img src=&quot;tg://emoji?id=5368324170671202286&quot; alt=&quot;<img class="emoji" src="//telegram.org/img/emoji/40/F09F918D.png" width="20" height="20" alt="👍" />&quot;/&gt;
&lt;tg-time unix=&quot;1647531900&quot; format=&quot;wDT&quot;&gt;22:45 tomorrow&lt;/tg-time&gt;
&lt;tg-math&gt;x^2 + y^2&lt;/tg-math&gt;

#hashtag $USD +12345678901, card: 4242 4242 4242 4242, https://t.me t.me a@t.me /command @username

all the text above was on the same line

&lt;h1&gt;Heading 1&lt;/h1&gt;
&lt;h2&gt;Heading 2&lt;/h2&gt;
&lt;h3&gt;Heading 3&lt;/h3&gt;
&lt;h4&gt;Heading 4&lt;/h4&gt;
&lt;h5&gt;Heading 5&lt;/h5&gt;
&lt;h6&gt;Heading 6&lt;/h6&gt;

&lt;a name=&quot;chapter-2&quot;&gt;&lt;/a&gt;

&lt;p&gt;Paragraph text&lt;/p&gt;
&lt;pre&gt;pre-formatted fixed-width code block&lt;/pre&gt;
&lt;pre&gt;&lt;code class=&quot;language-python&quot;&gt;  print(&#39;pre-formatted fixed-width code block written in the Python programming language&#39;)&lt;/code&gt;&lt;/pre&gt;
&lt;footer&gt;Footer text&lt;/footer&gt;
&lt;hr/&gt;
&lt;ul&gt;&lt;li&gt;unordered list item&lt;/li&gt;&lt;/ul&gt;
&lt;ol&gt;&lt;li&gt;ordered list item&lt;/li&gt;&lt;/ol&gt;
&lt;ol start=&quot;3&quot; type=&quot;a&quot; reversed&gt;&lt;li&gt;ordered list item&lt;/li&gt;&lt;/ol&gt;
&lt;ol&gt;&lt;li value=&quot;7&quot; type=&quot;i&quot;&gt;ordered list item with explicit number&lt;/li&gt;&lt;/ol&gt;
&lt;ul&gt;
&lt;li&gt;&lt;input type=&quot;checkbox&quot; checked&gt;Checked checkbox&lt;/li&gt;
&lt;li&gt;&lt;input type=&quot;checkbox&quot;&gt;Unchecked checkbox&lt;/li&gt;
&lt;/ul&gt;

&lt;blockquote&gt;Block quotation started&lt;br&gt;Block quotation continued&lt;br&gt;The last line of the block quotation&lt;cite&gt;The Author&lt;/cite&gt;&lt;/blockquote&gt;
&lt;aside&gt;Pull quote&lt;cite&gt;The Author&lt;/cite&gt;&lt;/aside&gt;

&lt;img src=&quot;https://telegram.org/example/photo.jpg&quot;/&gt;
&lt;video src=&quot;https://telegram.org/example/video.mp4&quot;&gt;&lt;/video&gt;
&lt;audio src=&quot;https://telegram.org/example/audio.mp3&quot;&gt;&lt;/audio&gt;
&lt;audio src=&quot;https://telegram.org/example/audio.ogg&quot;&gt;&lt;/audio&gt;
&lt;video src=&quot;https://telegram.org/example/animation.gif&quot;&gt;&lt;/video&gt;

&lt;figure&gt;&lt;img src=&quot;https://telegram.org/example/photo.jpg&quot; tg-spoiler/&gt;&lt;figcaption&gt;Photo caption&lt;cite&gt;Photo credit&lt;/cite&gt;&lt;/figcaption&gt;&lt;/figure&gt;
&lt;figure&gt;&lt;video src=&quot;https://telegram.org/example/video.mp4&quot; tg-spoiler&gt;&lt;/video&gt;&lt;figcaption&gt;Video caption&lt;/figcaption&gt;&lt;/figure&gt;
&lt;figure&gt;&lt;audio src=&quot;https://telegram.org/example/audio.mp3&quot;&gt;&lt;/audio&gt;&lt;figcaption&gt;Audio caption&lt;/figcaption&gt;&lt;/figure&gt;
&lt;figure&gt;&lt;audio src=&quot;https://telegram.org/example/audio.ogg&quot;&gt;&lt;/audio&gt;&lt;figcaption&gt;Voice note caption&lt;/figcaption&gt;&lt;/figure&gt;
&lt;figure&gt;&lt;video src=&quot;https://telegram.org/example/animation.gif&quot; tg-spoiler&gt;&lt;/video&gt;&lt;figcaption&gt;Animation caption&lt;/figcaption&gt;&lt;/figure&gt;

&lt;tg-map lat=&quot;41.9&quot; long=&quot;12.5&quot; zoom=&quot;14&quot;/&gt;
&lt;figure&gt;&lt;tg-map lat=&quot;41.9&quot; long=&quot;12.5&quot; zoom=&quot;14&quot;/&gt;&lt;figcaption&gt;Map caption&lt;/figcaption&gt;&lt;/figure&gt;

&lt;tg-collage&gt;&lt;img src=&quot;https://telegram.org/example/photo.jpg&quot;/&gt;&lt;video src=&quot;https://telegram.org/example/video.mp4&quot;/&gt;&lt;/tg-collage&gt;
&lt;tg-collage&gt;&lt;video src=&quot;https://telegram.org/example/video.mp4&quot;/&gt;&lt;img src=&quot;https://telegram.org/example/photo.jpg&quot;/&gt;&lt;figcaption&gt;Collage caption&lt;/figcaption&gt;&lt;/tg-collage&gt;
&lt;tg-slideshow&gt;&lt;img src=&quot;https://telegram.org/example/photo.jpg&quot;/&gt;&lt;video src=&quot;https://telegram.org/example/video.mp4&quot;/&gt;&lt;/tg-slideshow&gt;
&lt;tg-slideshow&gt;&lt;video src=&quot;https://telegram.org/example/video.mp4&quot;/&gt;&lt;img src=&quot;https://telegram.org/example/photo.jpg&quot;/&gt;&lt;figcaption&gt;Slideshow caption&lt;/figcaption&gt;&lt;/tg-slideshow&gt;

&lt;table&gt;&lt;tr&gt;&lt;th&gt;Header 1&lt;/th&gt;&lt;th&gt;Header 2&lt;/th&gt;&lt;/tr&gt;&lt;tr&gt;&lt;td&gt;Value 1&lt;/td&gt;&lt;td&gt;Value 2&lt;/td&gt;&lt;/tr&gt;&lt;/table&gt;
&lt;table bordered striped&gt;&lt;caption&gt;Table caption&lt;/caption&gt;
&lt;tr&gt;&lt;td colspan=&quot;2&quot; rowspan=&quot;2&quot; align=&quot;left&quot;&gt;Value&lt;/td&gt;&lt;td align=&quot;center&quot;&gt;Value2&lt;/td&gt;&lt;td align=&quot;right&quot;&gt;Value3&lt;/td&gt;&lt;/tr&gt;
&lt;tr&gt;&lt;td valign=&quot;top&quot;&gt;Value4&lt;/td&gt;&lt;td valign=&quot;middle&quot;&gt;Value5&lt;/td&gt;&lt;td valign=&quot;bottom&quot;&gt;Value6&lt;/td&gt;&lt;/tr&gt;
&lt;tr&gt;&lt;td&gt;Value7&lt;/td&gt;&lt;/tr&gt;&lt;/table&gt;

&lt;details&gt;&lt;summary&gt;Title&lt;/summary&gt;Content&lt;/details&gt;
&lt;details open&gt;&lt;summary&gt;Title&lt;/summary&gt;Content&lt;/details&gt;
&lt;tg-math-block&gt;E = mc^2&lt;/tg-math-block&gt;</code></pre>
<p>Please note:</p>
<ul>
<li>Only the tags mentioned above are currently supported.</li>
<li>All numerical HTML entities are supported.</li>
<li>The API currently supports only the following named HTML entities: <code>&amp;lt;</code>, <code>&amp;gt;</code>, <code>&amp;amp;</code>, <code>&amp;quot;</code>, <code>&amp;apos;</code>, <code>&amp;nbsp;</code>, <code>&amp;hellip;</code>, <code>&amp;mdash;</code>, <code>&amp;ndash;</code>, <code>&amp;lsquo;</code>, <code>&amp;rsquo;</code>, <code>&amp;ldquo;</code> and <code>&amp;rdquo;</code>.</li>
<li>Use nested <code>pre</code> and <code>code</code> tags to define the programming language for a pre-formatted block.</li>
<li>Programming language can&#39;t be specified for standalone <code>code</code> tags.</li>
<li>Links <code>mailto:...</code>, <code>tel:...</code>, and <code>tg://user?id=...</code> are rendered as e-mail links, phone links, and inline mentions respectively. Other supported links are rendered as regular inline links.</li>
<li>Images, videos, and audio files can be specified only as separate media blocks.</li>
<li>Media blocks support only HTTP and HTTPS URLs.</li>
<li>An empty <code>&lt;a name=&quot;...&quot;&gt;&lt;/a&gt;</code> on its own creates an anchor that can be linked to with <code>&lt;a href=&quot;#...&quot;&gt;...&lt;/a&gt;</code>.</li>
<li>In <code>&lt;figcaption&gt;</code>, you can use <code>&lt;cite&gt;</code> tags to specify caption credit.</li>
<li>Use <code>&lt;tg-reference name=&quot;...&quot;&gt;...&lt;/tg-reference&gt;</code> to define referenced text that can be linked to with <code>&lt;a href=&quot;#...&quot;&gt;...&lt;/a&gt;</code>.</li>
<li>The body of a <code>&lt;details&gt;</code> tag can contain rich message content. If the <code>open</code> attribute is specified, the block is expanded by default.</li>
<li>Formula source is treated as raw LaTeX.</li>
<li>See <a href="#date-time-entity-formatting">date-time entity formatting</a> for more details about supported date-time formats.</li>
</ul>
<h4><a class="anchor" name="richmessage" href="#richmessage"><i class="anchor-icon"></i></a>RichMessage</h4>
<p>Rich formatted message.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>blocks</td>
<td>Array of <a href="#richblock">RichBlock</a></td>
<td>Content of the message</td>
</tr>
<tr>
<td>is_rtl</td>
<td>Boolean</td>
<td><em>Optional</em>. <em>True</em>, if the rich message must be shown right-to-left</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="inputrichmessage" href="#inputrichmessage"><i class="anchor-icon"></i></a>InputRichMessage</h4>
<p>Describes a rich message to be sent. Exactly <strong>one</strong> of the fields <em>html</em> or <em>markdown</em> must be used.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>html</td>
<td>String</td>
<td><em>Optional</em>. Content of the rich message to send described using HTML formatting. See <a href="#rich-message-formatting-options">rich message formatting options</a> for more details.</td>
</tr>
<tr>
<td>markdown</td>
<td>String</td>
<td><em>Optional</em>. Content of the rich message to send described using Markdown formatting. See <a href="#rich-message-formatting-options">rich message formatting options</a> for more details.</td>
</tr>
<tr>
<td>is_rtl</td>
<td>Boolean</td>
<td><em>Optional</em>. Pass <em>True</em> if the rich message must be shown right-to-left</td>
</tr>
<tr>
<td>skip_entity_detection</td>
<td>Boolean</td>
<td><em>Optional</em>. Pass <em>True</em> to skip automatic detection of entities (e.g., URLs, email addresses, username mentions, hashtags, cashtags, bot commands, or phone numbers) in the text</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="sendrichmessage" href="#sendrichmessage"><i class="anchor-icon"></i></a>sendRichMessage</h4>
<p>Use this method to send rich messages. If the message contains a block with a media element, then the bot must have the right to send the media to the chat. On success, the sent <a href="#message">Message</a> is returned.</p>
<table class="table">
<thead>
<tr>
<th>Parameter</th>
<th>Type</th>
<th>Required</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>business_connection_id</td>
<td>String</td>
<td>Optional</td>
<td>Unique identifier of the business connection on behalf of which the message will be sent</td>
</tr>
<tr>
<td>chat_id</td>
<td>Integer or String</td>
<td>Yes</td>
<td>Unique identifier for the target chat or username of the target bot, supergroup or channel in the format <code>@username</code></td>
</tr>
<tr>
<td>message_thread_id</td>
<td>Integer</td>
<td>Optional</td>
<td>Unique identifier for the target message thread (topic) of a forum; for forum supergroups and private chats of bots with forum topic mode enabled only</td>
</tr>
<tr>
<td>direct_messages_topic_id</td>
<td>Integer</td>
<td>Optional</td>
<td>Identifier of the direct messages topic to which the message will be sent; required if the message is sent to a direct messages chat</td>
</tr>
<tr>
<td>rich_message</td>
<td><a href="#inputrichmessage">InputRichMessage</a></td>
<td>Yes</td>
<td>The message to be sent</td>
</tr>
<tr>
<td>disable_notification</td>
<td>Boolean</td>
<td>Optional</td>
<td>Sends the message <a href="https://telegram.org/blog/channels-2-0#silent-messages">silently</a>. Users will receive a notification with no sound.</td>
</tr>
<tr>
<td>protect_content</td>
<td>Boolean</td>
<td>Optional</td>
<td>Protects the contents of the sent message from forwarding and saving</td>
</tr>
<tr>
<td>allow_paid_broadcast</td>
<td>Boolean</td>
<td>Optional</td>
<td>Pass <em>True</em> to allow up to 1000 messages per second, ignoring <a href="https://core.telegram.org/bots/faq#how-can-i-message-all-of-my-bot-39s-subscribers-at-once">broadcasting limits</a> for a fee of 0.1 Telegram Stars per message. The relevant Stars will be withdrawn from the bot&#39;s balance.</td>
</tr>
<tr>
<td>message_effect_id</td>
<td>String</td>
<td>Optional</td>
<td>Unique identifier of the message effect to be added to the message; for private chats only</td>
</tr>
<tr>
<td>suggested_post_parameters</td>
<td><a href="#suggestedpostparameters">SuggestedPostParameters</a></td>
<td>Optional</td>
<td>A JSON-serialized object containing the parameters of the suggested post to send; for direct messages chats only. If the message is sent as a reply to another suggested post, then that suggested post is automatically declined.</td>
</tr>
<tr>
<td>reply_parameters</td>
<td><a href="#replyparameters">ReplyParameters</a></td>
<td>Optional</td>
<td>Description of the message to reply to</td>
</tr>
<tr>
<td>reply_markup</td>
<td><a href="#inlinekeyboardmarkup">InlineKeyboardMarkup</a> or <a href="#replykeyboardmarkup">ReplyKeyboardMarkup</a> or <a href="#replykeyboardremove">ReplyKeyboardRemove</a> or <a href="#forcereply">ForceReply</a></td>
<td>Optional</td>
<td>Additional interface options. A JSON-serialized object for an <a href="/bots/features#inline-keyboards">inline keyboard</a>, <a href="/bots/features#keyboards">custom reply keyboard</a>, instructions to remove a reply keyboard or to force a reply from the user.</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="sendrichmessagedraft" href="#sendrichmessagedraft"><i class="anchor-icon"></i></a>sendRichMessageDraft</h4>
<p>Use this method to stream a partial rich message to a user while the message is being generated. Note that the streamed draft is ephemeral and acts as a temporary 30-second preview - once the output is finalized, you <strong>must</strong> call <a href="#sendrichmessage">sendRichMessage</a> with the complete message to persist it in the user&#39;s chat. Returns <em>True</em> on success.</p>
<table class="table">
<thead>
<tr>
<th>Parameter</th>
<th>Type</th>
<th>Required</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>chat_id</td>
<td>Integer</td>
<td>Yes</td>
<td>Unique identifier for the target private chat</td>
</tr>
<tr>
<td>message_thread_id</td>
<td>Integer</td>
<td>Optional</td>
<td>Unique identifier for the target message thread</td>
</tr>
<tr>
<td>draft_id</td>
<td>Integer</td>
<td>Yes</td>
<td>Unique identifier of the message draft; must be non-zero. Changes to drafts with the same identifier are animated.</td>
</tr>
<tr>
<td>rich_message</td>
<td><a href="#inputrichmessage">InputRichMessage</a></td>
<td>Yes</td>
<td>The partial message to be streamed</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richtext" href="#richtext"><i class="anchor-icon"></i></a>RichText</h4>
<p>This object represents a rich formatted text. Currently, it can be either a String for plain text, an Array of <a href="#richtext">RichText</a>, or any of the following types:</p>
<ul>
<li><a href="#richtextbold">RichTextBold</a></li>
<li><a href="#richtextitalic">RichTextItalic</a></li>
<li><a href="#richtextunderline">RichTextUnderline</a></li>
<li><a href="#richtextstrikethrough">RichTextStrikethrough</a></li>
<li><a href="#richtextspoiler">RichTextSpoiler</a></li>
<li><a href="#richtextdatetime">RichTextDateTime</a></li>
<li><a href="#richtexttextmention">RichTextTextMention</a></li>
<li><a href="#richtextsubscript">RichTextSubscript</a></li>
<li><a href="#richtextsuperscript">RichTextSuperscript</a></li>
<li><a href="#richtextmarked">RichTextMarked</a></li>
<li><a href="#richtextcode">RichTextCode</a></li>
<li><a href="#richtextcustomemoji">RichTextCustomEmoji</a></li>
<li><a href="#richtextmathematicalexpression">RichTextMathematicalExpression</a></li>
<li><a href="#richtexturl">RichTextUrl</a></li>
<li><a href="#richtextemailaddress">RichTextEmailAddress</a></li>
<li><a href="#richtextphonenumber">RichTextPhoneNumber</a></li>
<li><a href="#richtextbankcardnumber">RichTextBankCardNumber</a></li>
<li><a href="#richtextmention">RichTextMention</a></li>
<li><a href="#richtexthashtag">RichTextHashtag</a></li>
<li><a href="#richtextcashtag">RichTextCashtag</a></li>
<li><a href="#richtextbotcommand">RichTextBotCommand</a></li>
<li><a href="#richtextanchor">RichTextAnchor</a></li>
<li><a href="#richtextanchorlink">RichTextAnchorLink</a></li>
<li><a href="#richtextreference">RichTextReference</a></li>
<li><a href="#richtextreferencelink">RichTextReferenceLink</a></li>
</ul>
<h4><a class="anchor" name="richtextbold" href="#richtextbold"><i class="anchor-icon"></i></a>RichTextBold</h4>
<p>A bold text.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the rich text, always “bold”</td>
</tr>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>The text</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richtextitalic" href="#richtextitalic"><i class="anchor-icon"></i></a>RichTextItalic</h4>
<p>An italicized text.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the rich text, always “italic”</td>
</tr>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>The text</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richtextunderline" href="#richtextunderline"><i class="anchor-icon"></i></a>RichTextUnderline</h4>
<p>An underlined text.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the rich text, always “underline”</td>
</tr>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>The text</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richtextstrikethrough" href="#richtextstrikethrough"><i class="anchor-icon"></i></a>RichTextStrikethrough</h4>
<p>A strikethrough text.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the rich text, always “strikethrough”</td>
</tr>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>The text</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richtextspoiler" href="#richtextspoiler"><i class="anchor-icon"></i></a>RichTextSpoiler</h4>
<p>A text covered by a spoiler.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the rich text, always “spoiler”</td>
</tr>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>The text</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richtextdatetime" href="#richtextdatetime"><i class="anchor-icon"></i></a>RichTextDateTime</h4>
<p>Formatted date and time.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the rich text, always “date_time”</td>
</tr>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>The text</td>
</tr>
<tr>
<td>unix_time</td>
<td>Integer</td>
<td>The Unix time associated with the entity</td>
</tr>
<tr>
<td>date_time_format</td>
<td>String</td>
<td>The string that defines the formatting of the date and time. See <a href="#date-time-entity-formatting">date-time entity formatting</a> for more details.</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richtexttextmention" href="#richtexttextmention"><i class="anchor-icon"></i></a>RichTextTextMention</h4>
<p>A mention of a Telegram user by their identifier.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the rich text, always “text_mention”</td>
</tr>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>The text</td>
</tr>
<tr>
<td>user</td>
<td><a href="#user">User</a></td>
<td>The mentioned user</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richtextsubscript" href="#richtextsubscript"><i class="anchor-icon"></i></a>RichTextSubscript</h4>
<p>A subscript text.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the rich text, always “subscript”</td>
</tr>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>The text</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richtextsuperscript" href="#richtextsuperscript"><i class="anchor-icon"></i></a>RichTextSuperscript</h4>
<p>A superscript text.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the rich text, always “superscript”</td>
</tr>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>The text</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richtextmarked" href="#richtextmarked"><i class="anchor-icon"></i></a>RichTextMarked</h4>
<p>A marked text.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the rich text, always “marked”</td>
</tr>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>The text</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richtextcode" href="#richtextcode"><i class="anchor-icon"></i></a>RichTextCode</h4>
<p>A monowidth text.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the rich text, always “code”</td>
</tr>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>The text</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richtextcustomemoji" href="#richtextcustomemoji"><i class="anchor-icon"></i></a>RichTextCustomEmoji</h4>
<p>A custom emoji.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the rich text, always “custom_emoji”</td>
</tr>
<tr>
<td>custom_emoji_id</td>
<td>String</td>
<td>Unique identifier of the custom emoji. Use <a href="#getcustomemojistickers">getCustomEmojiStickers</a> to get full information about the sticker.</td>
</tr>
<tr>
<td>alternative_text</td>
<td>String</td>
<td>Alternative emoji for the custom emoji</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richtextmathematicalexpression" href="#richtextmathematicalexpression"><i class="anchor-icon"></i></a>RichTextMathematicalExpression</h4>
<p>A mathematical expression.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the rich text, always “mathematical_expression”</td>
</tr>
<tr>
<td>expression</td>
<td>String</td>
<td>The expression in LaTeX format</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richtexturl" href="#richtexturl"><i class="anchor-icon"></i></a>RichTextUrl</h4>
<p>A text with a link.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the rich text, always “url”</td>
</tr>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>The text</td>
</tr>
<tr>
<td>url</td>
<td>String</td>
<td>URL of the link</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richtextemailaddress" href="#richtextemailaddress"><i class="anchor-icon"></i></a>RichTextEmailAddress</h4>
<p>A text with an email address.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the rich text, always “email_address”</td>
</tr>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>The text</td>
</tr>
<tr>
<td>email_address</td>
<td>String</td>
<td>The email address</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richtextphonenumber" href="#richtextphonenumber"><i class="anchor-icon"></i></a>RichTextPhoneNumber</h4>
<p>A text with a phone number.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the rich text, always “phone_number”</td>
</tr>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>The text</td>
</tr>
<tr>
<td>phone_number</td>
<td>String</td>
<td>The phone number</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richtextbankcardnumber" href="#richtextbankcardnumber"><i class="anchor-icon"></i></a>RichTextBankCardNumber</h4>
<p>A text with a bank card number.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the rich text, always “bank_card_number”</td>
</tr>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>The text</td>
</tr>
<tr>
<td>bank_card_number</td>
<td>String</td>
<td>The bank card number</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richtextmention" href="#richtextmention"><i class="anchor-icon"></i></a>RichTextMention</h4>
<p>A mention by a username.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the rich text, always “mention”</td>
</tr>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>The text</td>
</tr>
<tr>
<td>username</td>
<td>String</td>
<td>The username</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richtexthashtag" href="#richtexthashtag"><i class="anchor-icon"></i></a>RichTextHashtag</h4>
<p>A hashtag.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the rich text, always “hashtag”</td>
</tr>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>The text</td>
</tr>
<tr>
<td>hashtag</td>
<td>String</td>
<td>The hashtag</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richtextcashtag" href="#richtextcashtag"><i class="anchor-icon"></i></a>RichTextCashtag</h4>
<p>A cashtag.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the rich text, always “cashtag”</td>
</tr>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>The text</td>
</tr>
<tr>
<td>cashtag</td>
<td>String</td>
<td>The cashtag</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richtextbotcommand" href="#richtextbotcommand"><i class="anchor-icon"></i></a>RichTextBotCommand</h4>
<p>A bot command.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the rich text, always “bot_command”</td>
</tr>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>The text</td>
</tr>
<tr>
<td>bot_command</td>
<td>String</td>
<td>The bot command</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richtextanchor" href="#richtextanchor"><i class="anchor-icon"></i></a>RichTextAnchor</h4>
<p>An anchor.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the rich text, always “anchor”</td>
</tr>
<tr>
<td>name</td>
<td>String</td>
<td>The name of the anchor</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richtextanchorlink" href="#richtextanchorlink"><i class="anchor-icon"></i></a>RichTextAnchorLink</h4>
<p>A link to an anchor.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the rich text, always “anchor_link”</td>
</tr>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>The link text</td>
</tr>
<tr>
<td>anchor_name</td>
<td>String</td>
<td>The name of the anchor. If the name is empty, then the link brings back to the top of the message.</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richtextreference" href="#richtextreference"><i class="anchor-icon"></i></a>RichTextReference</h4>
<p>A reference.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the rich text, always “reference”</td>
</tr>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>Text of the reference</td>
</tr>
<tr>
<td>name</td>
<td>String</td>
<td>The name of the reference</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richtextreferencelink" href="#richtextreferencelink"><i class="anchor-icon"></i></a>RichTextReferenceLink</h4>
<p>A link to a reference.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the rich text, always “reference_link”</td>
</tr>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>The link text</td>
</tr>
<tr>
<td>reference_name</td>
<td>String</td>
<td>The name of the reference</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richblockcaption" href="#richblockcaption"><i class="anchor-icon"></i></a>RichBlockCaption</h4>
<p>Caption of a rich formatted block.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>Block caption</td>
</tr>
<tr>
<td>credit</td>
<td><a href="#richtext">RichText</a></td>
<td><em>Optional</em>. Block credit which corresponds to the HTML tag &lt;cite&gt;</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richblocktablecell" href="#richblocktablecell"><i class="anchor-icon"></i></a>RichBlockTableCell</h4>
<p>Cell in a table.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td><em>Optional</em>. Text in the cell. If omitted, then the cell is invisible.</td>
</tr>
<tr>
<td>is_header</td>
<td>True</td>
<td><em>Optional</em>. <em>True</em>, if the cell is a header cell</td>
</tr>
<tr>
<td>colspan</td>
<td>Integer</td>
<td><em>Optional</em>. The number of columns the cell spans if it is bigger than 1</td>
</tr>
<tr>
<td>rowspan</td>
<td>Integer</td>
<td><em>Optional</em>. The number of rows the cell spans if it is bigger than 1</td>
</tr>
<tr>
<td>align</td>
<td>String</td>
<td>Horizontal cell content alignment. Currently, must be one of “left”, “center”, or “right”.</td>
</tr>
<tr>
<td>valign</td>
<td>String</td>
<td>Vertical cell content alignment. Currently, must be one of “top”, “middle”, or “bottom”.</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richblocklistitem" href="#richblocklistitem"><i class="anchor-icon"></i></a>RichBlockListItem</h4>
<p>An item of a list.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>label</td>
<td>String</td>
<td>Label of the item</td>
</tr>
<tr>
<td>blocks</td>
<td>Array of <a href="#richblock">RichBlock</a></td>
<td>The content of the item</td>
</tr>
<tr>
<td>has_checkbox</td>
<td>True</td>
<td><em>Optional</em>. <em>True</em>, if the item has a checkbox</td>
</tr>
<tr>
<td>is_checked</td>
<td>True</td>
<td><em>Optional</em>. <em>True</em>, if the item has a checked checkbox</td>
</tr>
<tr>
<td>value</td>
<td>Integer</td>
<td><em>Optional</em>. For ordered lists, the numeric value of the item label</td>
</tr>
<tr>
<td>type</td>
<td>String</td>
<td><em>Optional</em>. For ordered lists, the type of the item label; must be one of “a” for lowercase letters, “A” for uppercase letters, “i” for lowercase Roman numerals, “I” for uppercase Roman numerals, or “1” for decimal numbers</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richblock" href="#richblock"><i class="anchor-icon"></i></a>RichBlock</h4>
<p>This object represents a block in a rich formatted message. Currently, it can be any of the following types:</p>
<ul>
<li><a href="#richblockparagraph">RichBlockParagraph</a></li>
<li><a href="#richblocksectionheading">RichBlockSectionHeading</a></li>
<li><a href="#richblockpreformatted">RichBlockPreformatted</a></li>
<li><a href="#richblockfooter">RichBlockFooter</a></li>
<li><a href="#richblockdivider">RichBlockDivider</a></li>
<li><a href="#richblockmathematicalexpression">RichBlockMathematicalExpression</a></li>
<li><a href="#richblockanchor">RichBlockAnchor</a></li>
<li><a href="#richblocklist">RichBlockList</a></li>
<li><a href="#richblockblockquotation">RichBlockBlockQuotation</a></li>
<li><a href="#richblockpullquotation">RichBlockPullQuotation</a></li>
<li><a href="#richblockcollage">RichBlockCollage</a></li>
<li><a href="#richblockslideshow">RichBlockSlideshow</a></li>
<li><a href="#richblocktable">RichBlockTable</a></li>
<li><a href="#richblockdetails">RichBlockDetails</a></li>
<li><a href="#richblockmap">RichBlockMap</a></li>
<li><a href="#richblockanimation">RichBlockAnimation</a></li>
<li><a href="#richblockaudio">RichBlockAudio</a></li>
<li><a href="#richblockphoto">RichBlockPhoto</a></li>
<li><a href="#richblockvideo">RichBlockVideo</a></li>
<li><a href="#richblockvoicenote">RichBlockVoiceNote</a></li>
<li><a href="#richblockthinking">RichBlockThinking</a></li>
</ul>
<h4><a class="anchor" name="richblockparagraph" href="#richblockparagraph"><i class="anchor-icon"></i></a>RichBlockParagraph</h4>
<p>A text paragraph, corresponding to the HTML tag <code>&lt;p&gt;</code>.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the block, always “paragraph”</td>
</tr>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>Text of the block</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richblocksectionheading" href="#richblocksectionheading"><i class="anchor-icon"></i></a>RichBlockSectionHeading</h4>
<p>A section heading, corresponding to the HTML tags <code>&lt;h1&gt;</code>, <code>&lt;h2&gt;</code>, <code>&lt;h3&gt;</code>, <code>&lt;h4&gt;</code>, <code>&lt;h5&gt;</code>, or <code>&lt;h6&gt;</code>.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the block, always “heading”</td>
</tr>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>Text of the block</td>
</tr>
<tr>
<td>size</td>
<td>Integer</td>
<td>Relative size of the text font; 1-6, 1 is the largest, 6 is the smallest</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richblockpreformatted" href="#richblockpreformatted"><i class="anchor-icon"></i></a>RichBlockPreformatted</h4>
<p>A preformatted text block, corresponding to the nested HTML tags <code>&lt;pre&gt;</code> and <code>&lt;code&gt;</code>.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the block, always “pre”</td>
</tr>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>Text of the block</td>
</tr>
<tr>
<td>language</td>
<td>String</td>
<td><em>Optional</em>. The programming language of the text</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richblockfooter" href="#richblockfooter"><i class="anchor-icon"></i></a>RichBlockFooter</h4>
<p>A footer, corresponding to the HTML tag <code>&lt;footer&gt;</code>.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the block, always “footer”</td>
</tr>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>Text of the block</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richblockdivider" href="#richblockdivider"><i class="anchor-icon"></i></a>RichBlockDivider</h4>
<p>A divider, corresponding to the HTML tag <code>&lt;hr/&gt;</code>.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the block, always “divider”</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richblockmathematicalexpression" href="#richblockmathematicalexpression"><i class="anchor-icon"></i></a>RichBlockMathematicalExpression</h4>
<p>A block with a mathematical expression in LaTeX format, corresponding to the custom HTML tag <code>&lt;tg-math-block&gt;</code>.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the block, always “mathematical_expression”</td>
</tr>
<tr>
<td>expression</td>
<td>String</td>
<td>The mathematical expression in LaTeX format</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richblockanchor" href="#richblockanchor"><i class="anchor-icon"></i></a>RichBlockAnchor</h4>
<p>A block with an anchor, corresponding to the HTML tag <code>&lt;a&gt;</code> with the attribute <code>name</code>.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the block, always “anchor”</td>
</tr>
<tr>
<td>name</td>
<td>String</td>
<td>The name of the anchor</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richblocklist" href="#richblocklist"><i class="anchor-icon"></i></a>RichBlockList</h4>
<p>A list of blocks, corresponding to the HTML tag <code>&lt;ul&gt;</code> or <code>&lt;ol&gt;</code> with multiple nested tags <code>&lt;li&gt;</code>.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the block, always “list”</td>
</tr>
<tr>
<td>items</td>
<td>Array of <a href="#richblocklistitem">RichBlockListItem</a></td>
<td>Items of the list</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richblockblockquotation" href="#richblockblockquotation"><i class="anchor-icon"></i></a>RichBlockBlockQuotation</h4>
<p>A block quotation, corresponding to the HTML tag <code>&lt;blockquote&gt;</code>.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the block, always “blockquote”</td>
</tr>
<tr>
<td>blocks</td>
<td>Array of <a href="#richblock">RichBlock</a></td>
<td>Content of the block</td>
</tr>
<tr>
<td>credit</td>
<td><a href="#richtext">RichText</a></td>
<td><em>Optional</em>. Credit of the block</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richblockpullquotation" href="#richblockpullquotation"><i class="anchor-icon"></i></a>RichBlockPullQuotation</h4>
<p>A quotation with centered text, loosely corresponding to the HTML tag <code>&lt;aside&gt;</code>.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the block, always “pullquote”</td>
</tr>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>Text of the block</td>
</tr>
<tr>
<td>credit</td>
<td><a href="#richtext">RichText</a></td>
<td><em>Optional</em>. Credit of the block</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richblockcollage" href="#richblockcollage"><i class="anchor-icon"></i></a>RichBlockCollage</h4>
<p>A collage, corresponding to the custom HTML tag <code>&lt;tg-collage&gt;</code>.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the block, always “collage”</td>
</tr>
<tr>
<td>blocks</td>
<td>Array of <a href="#richblock">RichBlock</a></td>
<td>Elements of the collage</td>
</tr>
<tr>
<td>caption</td>
<td><a href="#richblockcaption">RichBlockCaption</a></td>
<td><em>Optional</em>. Caption of the block</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richblockslideshow" href="#richblockslideshow"><i class="anchor-icon"></i></a>RichBlockSlideshow</h4>
<p>A slideshow, corresponding to the custom HTML tag <code>&lt;tg-slideshow&gt;</code>.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the block, always “slideshow”</td>
</tr>
<tr>
<td>blocks</td>
<td>Array of <a href="#richblock">RichBlock</a></td>
<td>Elements of the slideshow</td>
</tr>
<tr>
<td>caption</td>
<td><a href="#richblockcaption">RichBlockCaption</a></td>
<td><em>Optional</em>. Caption of the block</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richblocktable" href="#richblocktable"><i class="anchor-icon"></i></a>RichBlockTable</h4>
<p>A table, corresponding to the HTML tag <code>&lt;table&gt;</code>.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the block, always “table”</td>
</tr>
<tr>
<td>cells</td>
<td>Array of Array of <a href="#richblocktablecell">RichBlockTableCell</a></td>
<td>Cells of the table</td>
</tr>
<tr>
<td>is_bordered</td>
<td>True</td>
<td><em>Optional</em>. <em>True</em>, if the table has borders</td>
</tr>
<tr>
<td>is_striped</td>
<td>True</td>
<td><em>Optional</em>. <em>True</em>, if the table is striped</td>
</tr>
<tr>
<td>caption</td>
<td><a href="#richtext">RichText</a></td>
<td><em>Optional</em>. Caption of the table</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richblockdetails" href="#richblockdetails"><i class="anchor-icon"></i></a>RichBlockDetails</h4>
<p>An expandable block for details disclosure, corresponding to the HTML tag <code>&lt;details&gt;</code>.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the block, always “details”</td>
</tr>
<tr>
<td>summary</td>
<td><a href="#richtext">RichText</a></td>
<td>Always shown summary of the block</td>
</tr>
<tr>
<td>blocks</td>
<td>Array of <a href="#richblock">RichBlock</a></td>
<td>Content of the block</td>
</tr>
<tr>
<td>is_open</td>
<td>True</td>
<td><em>Optional</em>. <em>True</em>, if the content of the block is visible by default</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richblockmap" href="#richblockmap"><i class="anchor-icon"></i></a>RichBlockMap</h4>
<p>A block with a map, corresponding to the custom HTML tag <code>&lt;tg-map&gt;</code>.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the block, always “map”</td>
</tr>
<tr>
<td>location</td>
<td><a href="#location">Location</a></td>
<td>Location of the center of the map</td>
</tr>
<tr>
<td>zoom</td>
<td>Integer</td>
<td>Map zoom level; 13-20</td>
</tr>
<tr>
<td>width</td>
<td>Integer</td>
<td>Expected width of the map</td>
</tr>
<tr>
<td>height</td>
<td>Integer</td>
<td>Expected height of the map</td>
</tr>
<tr>
<td>caption</td>
<td><a href="#richblockcaption">RichBlockCaption</a></td>
<td><em>Optional</em>. Caption of the block</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richblockanimation" href="#richblockanimation"><i class="anchor-icon"></i></a>RichBlockAnimation</h4>
<p>A block with an animation, corresponding to the HTML tag <code>&lt;video&gt;</code>.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the block, always “animation”</td>
</tr>
<tr>
<td>animation</td>
<td><a href="#animation">Animation</a></td>
<td>The animation</td>
</tr>
<tr>
<td>has_spoiler</td>
<td>True</td>
<td><em>Optional</em>. <em>True</em>, if the media preview is covered by a spoiler animation</td>
</tr>
<tr>
<td>caption</td>
<td><a href="#richblockcaption">RichBlockCaption</a></td>
<td><em>Optional</em>. Caption of the block</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richblockaudio" href="#richblockaudio"><i class="anchor-icon"></i></a>RichBlockAudio</h4>
<p>A block with a music file, corresponding to the HTML tag <code>&lt;audio&gt;</code>.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the block, always “audio”</td>
</tr>
<tr>
<td>audio</td>
<td><a href="#audio">Audio</a></td>
<td>The audio</td>
</tr>
<tr>
<td>caption</td>
<td><a href="#richblockcaption">RichBlockCaption</a></td>
<td><em>Optional</em>. Caption of the block</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richblockphoto" href="#richblockphoto"><i class="anchor-icon"></i></a>RichBlockPhoto</h4>
<p>A block with a photo, corresponding to the HTML tag <code>&lt;photo&gt;</code>.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the block, always “photo”</td>
</tr>
<tr>
<td>photo</td>
<td>Array of <a href="#photosize">PhotoSize</a></td>
<td>Available sizes of the photo</td>
</tr>
<tr>
<td>has_spoiler</td>
<td>True</td>
<td><em>Optional</em>. <em>True</em>, if the media preview is covered by a spoiler animation</td>
</tr>
<tr>
<td>caption</td>
<td><a href="#richblockcaption">RichBlockCaption</a></td>
<td><em>Optional</em>. Caption of the block</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richblockvideo" href="#richblockvideo"><i class="anchor-icon"></i></a>RichBlockVideo</h4>
<p>A block with a video, corresponding to the HTML tag <code>&lt;video&gt;</code>.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the block, always “video”</td>
</tr>
<tr>
<td>video</td>
<td><a href="#video">Video</a></td>
<td>The video</td>
</tr>
<tr>
<td>has_spoiler</td>
<td>True</td>
<td><em>Optional</em>. <em>True</em>, if the media preview is covered by a spoiler animation</td>
</tr>
<tr>
<td>caption</td>
<td><a href="#richblockcaption">RichBlockCaption</a></td>
<td><em>Optional</em>. Caption of the block</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richblockvoicenote" href="#richblockvoicenote"><i class="anchor-icon"></i></a>RichBlockVoiceNote</h4>
<p>A block with a voice note, corresponding to the HTML tag <code>&lt;audio&gt;</code>.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the block, always “voice_note”</td>
</tr>
<tr>
<td>voice_note</td>
<td><a href="#voice">Voice</a></td>
<td>The voice note</td>
</tr>
<tr>
<td>caption</td>
<td><a href="#richblockcaption">RichBlockCaption</a></td>
<td><em>Optional</em>. Caption of the block</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="richblockthinking" href="#richblockthinking"><i class="anchor-icon"></i></a>RichBlockThinking</h4>
<p>A block with a “Thinking…” placeholder, corresponding to the custom HTML tag <code>&lt;tg-thinking&gt;</code>. The block may be used only in <a href="#sendrichmessagedraft">sendRichMessageDraft</a>, therefore it can&#39;t be received in messages. See <a href="https://t.me/addemoji/AIActions"><a href="https://t.me/addemoji/AIActions">https://t.me/addemoji/AIActions</a></a> for examples of custom emoji, which are recommended for usage in the block.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the block, always “thinking”</td>
</tr>
<tr>
<td>text</td>
<td><a href="#richtext">RichText</a></td>
<td>Text of the block. See <a href="https://t.me/addemoji/AIActions"><a href="https://t.me/addemoji/AIActions">https://t.me/addemoji/AIActions</a></a> for examples of custom emoji, which are recommended for usage in the block.</td>
</tr>
</tbody>
</table>
<h3><a class="anchor" name="inline-mode" href="#inline-mode"><i class="anchor-icon"></i></a>Inline mode</h3>
<p>The following methods and objects allow your bot to work in <a href="/bots/inline">inline mode</a>.<br>Please see our <a href="/bots/inline">Introduction to Inline bots</a> for more details.</p>
<p>To enable this option, send the <code>/setinline</code> command to <a href="https://t.me/botfather">@BotFather</a> and provide the placeholder text that the user will see in the input field after typing your bot&#39;s name.</p>
<h4><a class="anchor" name="inlinequery" href="#inlinequery"><i class="anchor-icon"></i></a>InlineQuery</h4>
<p>This object represents an incoming inline query. When the user sends an empty query, your bot could return some default or trending results.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>id</td>
<td>String</td>
<td>Unique identifier for this query</td>
</tr>
<tr>
<td>from</td>
<td><a href="#user">User</a></td>
<td>Sender</td>
</tr>
<tr>
<td>query</td>
<td>String</td>
<td>Text of the query (up to 256 characters)</td>
</tr>
<tr>
<td>offset</td>
<td>String</td>
<td>Offset of the results to be returned, can be controlled by the bot</td>
</tr>
<tr>
<td>chat_type</td>
<td>String</td>
<td><em>Optional</em>. Type of the chat from which the inline query was sent. Can be either “sender” for a private chat with the inline query sender, “private”, “group”, “supergroup”, or “channel”. The chat type should be always known for requests sent from official clients and most third-party clients, unless the request was sent from a secret chat.</td>
</tr>
<tr>
<td>location</td>
<td><a href="#location">Location</a></td>
<td><em>Optional</em>. Sender location, only for bots that request user location</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="answerinlinequery" href="#answerinlinequery"><i class="anchor-icon"></i></a>answerInlineQuery</h4>
<p>Use this method to send answers to an inline query. On success, <em>True</em> is returned.<br>No more than <strong>50</strong> results per query are allowed.</p>
<table class="table">
<thead>
<tr>
<th>Parameter</th>
<th>Type</th>
<th>Required</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>inline_query_id</td>
<td>String</td>
<td>Yes</td>
<td>Unique identifier for the answered query</td>
</tr>
<tr>
<td>results</td>
<td>Array of <a href="#inlinequeryresult">InlineQueryResult</a></td>
<td>Yes</td>
<td>A JSON-serialized array of results for the inline query</td>
</tr>
<tr>
<td>cache_time</td>
<td>Integer</td>
<td>Optional</td>
<td>The maximum amount of time in seconds that the result of the inline query may be cached on the server. Defaults to 300.</td>
</tr>
<tr>
<td>is_personal</td>
<td>Boolean</td>
<td>Optional</td>
<td>Pass <em>True</em> if results may be cached on the server side only for the user that sent the query. By default, results may be returned to any user who sends the same query.</td>
</tr>
<tr>
<td>next_offset</td>
<td>String</td>
<td>Optional</td>
<td>Pass the offset that a client should send in the next query with the same text to receive more results. Pass an empty string if there are no more results or if you don&#39;t support pagination. Offset length can&#39;t exceed 64 bytes.</td>
</tr>
<tr>
<td>button</td>
<td><a href="#inlinequeryresultsbutton">InlineQueryResultsButton</a></td>
<td>Optional</td>
<td>A JSON-serialized object describing a button to be shown above inline query results</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="inlinequeryresultsbutton" href="#inlinequeryresultsbutton"><i class="anchor-icon"></i></a>InlineQueryResultsButton</h4>
<p>This object represents a button to be shown above inline query results. You <strong>must</strong> use exactly one of the optional fields.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>text</td>
<td>String</td>
<td>Label text on the button</td>
</tr>
<tr>
<td>web_app</td>
<td><a href="#webappinfo">WebAppInfo</a></td>
<td><em>Optional</em>. Description of the <a href="/bots/webapps">Web App</a> that will be launched when the user presses the button. The Web App will be able to switch back to the inline mode using the method <a href="/bots/webapps#initializing-mini-apps">switchInlineQuery</a> inside the Web App.</td>
</tr>
<tr>
<td>start_parameter</td>
<td>String</td>
<td><em>Optional</em>. <a href="/bots/features#deep-linking">Deep-linking</a> parameter for the /start message sent to the bot when a user presses the button. 1-64 characters, only <code>A-Z</code>, <code>a-z</code>, <code>0-9</code>, <code>_</code> and <code>-</code> are allowed.<br><br><em>Example:</em> An inline bot that sends YouTube videos can ask the user to connect the bot to their YouTube account to adapt search results accordingly. To do this, it displays a &#39;Connect your YouTube account&#39; button above the results, or even before showing any. The user presses the button, switches to a private chat with the bot and, in doing so, passes a start parameter that instructs the bot to return an OAuth link. Once done, the bot can offer a <a href="#inlinekeyboardmarkup"><em>switch_inline</em></a> button so that the user can easily return to the chat where they wanted to use the bot&#39;s inline capabilities.</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="inlinequeryresult" href="#inlinequeryresult"><i class="anchor-icon"></i></a>InlineQueryResult</h4>
<p>This object represents one result of an inline query. Telegram clients currently support results of the following 20 types:</p>
<ul>
<li><a href="#inlinequeryresultcachedaudio">InlineQueryResultCachedAudio</a></li>
<li><a href="#inlinequeryresultcacheddocument">InlineQueryResultCachedDocument</a></li>
<li><a href="#inlinequeryresultcachedgif">InlineQueryResultCachedGif</a></li>
<li><a href="#inlinequeryresultcachedmpeg4gif">InlineQueryResultCachedMpeg4Gif</a></li>
<li><a href="#inlinequeryresultcachedphoto">InlineQueryResultCachedPhoto</a></li>
<li><a href="#inlinequeryresultcachedsticker">InlineQueryResultCachedSticker</a></li>
<li><a href="#inlinequeryresultcachedvideo">InlineQueryResultCachedVideo</a></li>
<li><a href="#inlinequeryresultcachedvoice">InlineQueryResultCachedVoice</a></li>
<li><a href="#inlinequeryresultarticle">InlineQueryResultArticle</a></li>
<li><a href="#inlinequeryresultaudio">InlineQueryResultAudio</a></li>
<li><a href="#inlinequeryresultcontact">InlineQueryResultContact</a></li>
<li><a href="#inlinequeryresultgame">InlineQueryResultGame</a></li>
<li><a href="#inlinequeryresultdocument">InlineQueryResultDocument</a></li>
<li><a href="#inlinequeryresultgif">InlineQueryResultGif</a></li>
<li><a href="#inlinequeryresultlocation">InlineQueryResultLocation</a></li>
<li><a href="#inlinequeryresultmpeg4gif">InlineQueryResultMpeg4Gif</a></li>
<li><a href="#inlinequeryresultphoto">InlineQueryResultPhoto</a></li>
<li><a href="#inlinequeryresultvenue">InlineQueryResultVenue</a></li>
<li><a href="#inlinequeryresultvideo">InlineQueryResultVideo</a></li>
<li><a href="#inlinequeryresultvoice">InlineQueryResultVoice</a></li>
</ul>
<p><strong>Note:</strong> All URLs passed in inline query results will be available to end users and therefore must be assumed to be <strong>public</strong>.</p>
<h4><a class="anchor" name="inlinequeryresultarticle" href="#inlinequeryresultarticle"><i class="anchor-icon"></i></a>InlineQueryResultArticle</h4>
<p>Represents a link to an article or web page.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the result, must be <em>article</em></td>
</tr>
<tr>
<td>id</td>
<td>String</td>
<td>Unique identifier for this result, 1-64 Bytes</td>
</tr>
<tr>
<td>title</td>
<td>String</td>
<td>Title of the result</td>
</tr>
<tr>
<td>input_message_content</td>
<td><a href="#inputmessagecontent">InputMessageContent</a></td>
<td>Content of the message to be sent</td>
</tr>
<tr>
<td>reply_markup</td>
<td><a href="#inlinekeyboardmarkup">InlineKeyboardMarkup</a></td>
<td><em>Optional</em>. <a href="/bots/features#inline-keyboards">Inline keyboard</a> attached to the message</td>
</tr>
<tr>
<td>url</td>
<td>String</td>
<td><em>Optional</em>. URL of the result</td>
</tr>
<tr>
<td>description</td>
<td>String</td>
<td><em>Optional</em>. Short description of the result</td>
</tr>
<tr>
<td>thumbnail_url</td>
<td>String</td>
<td><em>Optional</em>. Url of the thumbnail for the result</td>
</tr>
<tr>
<td>thumbnail_width</td>
<td>Integer</td>
<td><em>Optional</em>. Thumbnail width</td>
</tr>
<tr>
<td>thumbnail_height</td>
<td>Integer</td>
<td><em>Optional</em>. Thumbnail height</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="inlinequeryresultphoto" href="#inlinequeryresultphoto"><i class="anchor-icon"></i></a>InlineQueryResultPhoto</h4>
<p>Represents a link to a photo. By default, this photo will be sent by the user with optional caption. Alternatively, you can use <em>input_message_content</em> to send a message with the specified content instead of the photo.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the result, must be <em>photo</em></td>
</tr>
<tr>
<td>id</td>
<td>String</td>
<td>Unique identifier for this result, 1-64 bytes</td>
</tr>
<tr>
<td>photo_url</td>
<td>String</td>
<td>A valid URL of the photo. Photo must be in <strong>JPEG</strong> format. Photo size must not exceed 5MB.</td>
</tr>
<tr>
<td>thumbnail_url</td>
<td>String</td>
<td>URL of the thumbnail for the photo</td>
</tr>
<tr>
<td>photo_width</td>
<td>Integer</td>
<td><em>Optional</em>. Width of the photo</td>
</tr>
<tr>
<td>photo_height</td>
<td>Integer</td>
<td><em>Optional</em>. Height of the photo</td>
</tr>
<tr>
<td>title</td>
<td>String</td>
<td><em>Optional</em>. Title for the result</td>
</tr>
<tr>
<td>description</td>
<td>String</td>
<td><em>Optional</em>. Short description of the result</td>
</tr>
<tr>
<td>caption</td>
<td>String</td>
<td><em>Optional</em>. Caption of the photo to be sent, 0-1024 characters after entities parsing</td>
</tr>
<tr>
<td>parse_mode</td>
<td>String</td>
<td><em>Optional</em>. Mode for parsing entities in the photo caption. See <a href="#formatting-options">formatting options</a> for more details.</td>
</tr>
<tr>
<td>caption_entities</td>
<td>Array of <a href="#messageentity">MessageEntity</a></td>
<td><em>Optional</em>. List of special entities that appear in the caption, which can be specified instead of <em>parse_mode</em></td>
</tr>
<tr>
<td>show_caption_above_media</td>
<td>Boolean</td>
<td><em>Optional</em>. Pass <em>True</em>, if the caption must be shown above the message media</td>
</tr>
<tr>
<td>reply_markup</td>
<td><a href="#inlinekeyboardmarkup">InlineKeyboardMarkup</a></td>
<td><em>Optional</em>. <a href="/bots/features#inline-keyboards">Inline keyboard</a> attached to the message</td>
</tr>
<tr>
<td>input_message_content</td>
<td><a href="#inputmessagecontent">InputMessageContent</a></td>
<td><em>Optional</em>. Content of the message to be sent instead of the photo</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="inlinequeryresultgif" href="#inlinequeryresultgif"><i class="anchor-icon"></i></a>InlineQueryResultGif</h4>
<p>Represents a link to an animated GIF file. By default, this animated GIF file will be sent by the user with optional caption. Alternatively, you can use <em>input_message_content</em> to send a message with the specified content instead of the animation.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the result, must be <em>gif</em></td>
</tr>
<tr>
<td>id</td>
<td>String</td>
<td>Unique identifier for this result, 1-64 bytes</td>
</tr>
<tr>
<td>gif_url</td>
<td>String</td>
<td>A valid URL for the GIF file</td>
</tr>
<tr>
<td>gif_width</td>
<td>Integer</td>
<td><em>Optional</em>. Width of the GIF</td>
</tr>
<tr>
<td>gif_height</td>
<td>Integer</td>
<td><em>Optional</em>. Height of the GIF</td>
</tr>
<tr>
<td>gif_duration</td>
<td>Integer</td>
<td><em>Optional</em>. Duration of the GIF in seconds</td>
</tr>
<tr>
<td>thumbnail_url</td>
<td>String</td>
<td>URL of the static (JPEG or GIF) or animated (MPEG4) thumbnail for the result</td>
</tr>
<tr>
<td>thumbnail_mime_type</td>
<td>String</td>
<td><em>Optional</em>. MIME type of the thumbnail, must be one of “image/jpeg”, “image/gif”, or “video/mp4”. Defaults to “image/jpeg”.</td>
</tr>
<tr>
<td>title</td>
<td>String</td>
<td><em>Optional</em>. Title for the result</td>
</tr>
<tr>
<td>caption</td>
<td>String</td>
<td><em>Optional</em>. Caption of the GIF file to be sent, 0-1024 characters after entities parsing</td>
</tr>
<tr>
<td>parse_mode</td>
<td>String</td>
<td><em>Optional</em>. Mode for parsing entities in the caption. See <a href="#formatting-options">formatting options</a> for more details.</td>
</tr>
<tr>
<td>caption_entities</td>
<td>Array of <a href="#messageentity">MessageEntity</a></td>
<td><em>Optional</em>. List of special entities that appear in the caption, which can be specified instead of <em>parse_mode</em></td>
</tr>
<tr>
<td>show_caption_above_media</td>
<td>Boolean</td>
<td><em>Optional</em>. Pass <em>True</em>, if the caption must be shown above the message media</td>
</tr>
<tr>
<td>reply_markup</td>
<td><a href="#inlinekeyboardmarkup">InlineKeyboardMarkup</a></td>
<td><em>Optional</em>. <a href="/bots/features#inline-keyboards">Inline keyboard</a> attached to the message</td>
</tr>
<tr>
<td>input_message_content</td>
<td><a href="#inputmessagecontent">InputMessageContent</a></td>
<td><em>Optional</em>. Content of the message to be sent instead of the GIF animation</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="inlinequeryresultmpeg4gif" href="#inlinequeryresultmpeg4gif"><i class="anchor-icon"></i></a>InlineQueryResultMpeg4Gif</h4>
<p>Represents a link to a video animation (H.264/MPEG-4 AVC video without sound). By default, this animated MPEG-4 file will be sent by the user with optional caption. Alternatively, you can use <em>input_message_content</em> to send a message with the specified content instead of the animation.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the result, must be <em>mpeg4_gif</em></td>
</tr>
<tr>
<td>id</td>
<td>String</td>
<td>Unique identifier for this result, 1-64 bytes</td>
</tr>
<tr>
<td>mpeg4_url</td>
<td>String</td>
<td>A valid URL for the MPEG4 file</td>
</tr>
<tr>
<td>mpeg4_width</td>
<td>Integer</td>
<td><em>Optional</em>. Video width</td>
</tr>
<tr>
<td>mpeg4_height</td>
<td>Integer</td>
<td><em>Optional</em>. Video height</td>
</tr>
<tr>
<td>mpeg4_duration</td>
<td>Integer</td>
<td><em>Optional</em>. Video duration in seconds</td>
</tr>
<tr>
<td>thumbnail_url</td>
<td>String</td>
<td>URL of the static (JPEG or GIF) or animated (MPEG4) thumbnail for the result</td>
</tr>
<tr>
<td>thumbnail_mime_type</td>
<td>String</td>
<td><em>Optional</em>. MIME type of the thumbnail, must be one of “image/jpeg”, “image/gif”, or “video/mp4”. Defaults to “image/jpeg”.</td>
</tr>
<tr>
<td>title</td>
<td>String</td>
<td><em>Optional</em>. Title for the result</td>
</tr>
<tr>
<td>caption</td>
<td>String</td>
<td><em>Optional</em>. Caption of the MPEG-4 file to be sent, 0-1024 characters after entities parsing</td>
</tr>
<tr>
<td>parse_mode</td>
<td>String</td>
<td><em>Optional</em>. Mode for parsing entities in the caption. See <a href="#formatting-options">formatting options</a> for more details.</td>
</tr>
<tr>
<td>caption_entities</td>
<td>Array of <a href="#messageentity">MessageEntity</a></td>
<td><em>Optional</em>. List of special entities that appear in the caption, which can be specified instead of <em>parse_mode</em></td>
</tr>
<tr>
<td>show_caption_above_media</td>
<td>Boolean</td>
<td><em>Optional</em>. Pass <em>True</em>, if the caption must be shown above the message media</td>
</tr>
<tr>
<td>reply_markup</td>
<td><a href="#inlinekeyboardmarkup">InlineKeyboardMarkup</a></td>
<td><em>Optional</em>. <a href="/bots/features#inline-keyboards">Inline keyboard</a> attached to the message</td>
</tr>
<tr>
<td>input_message_content</td>
<td><a href="#inputmessagecontent">InputMessageContent</a></td>
<td><em>Optional</em>. Content of the message to be sent instead of the video animation</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="inlinequeryresultvideo" href="#inlinequeryresultvideo"><i class="anchor-icon"></i></a>InlineQueryResultVideo</h4>
<p>Represents a link to a page containing an embedded video player or a video file. By default, this video file will be sent by the user with an optional caption. Alternatively, you can use <em>input_message_content</em> to send a message with the specified content instead of the video.</p>
<blockquote>
<p>If an InlineQueryResultVideo message contains an embedded video (e.g., YouTube), you <strong>must</strong> replace its content using <em>input_message_content</em>.</p>
</blockquote>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the result, must be <em>video</em></td>
</tr>
<tr>
<td>id</td>
<td>String</td>
<td>Unique identifier for this result, 1-64 bytes</td>
</tr>
<tr>
<td>video_url</td>
<td>String</td>
<td>A valid URL for the embedded video player or video file</td>
</tr>
<tr>
<td>mime_type</td>
<td>String</td>
<td>MIME type of the content of the video URL, “text/html” or “video/mp4”</td>
</tr>
<tr>
<td>thumbnail_url</td>
<td>String</td>
<td>URL of the thumbnail (JPEG only) for the video</td>
</tr>
<tr>
<td>title</td>
<td>String</td>
<td>Title for the result</td>
</tr>
<tr>
<td>caption</td>
<td>String</td>
<td><em>Optional</em>. Caption of the video to be sent, 0-1024 characters after entities parsing</td>
</tr>
<tr>
<td>parse_mode</td>
<td>String</td>
<td><em>Optional</em>. Mode for parsing entities in the video caption. See <a href="#formatting-options">formatting options</a> for more details.</td>
</tr>
<tr>
<td>caption_entities</td>
<td>Array of <a href="#messageentity">MessageEntity</a></td>
<td><em>Optional</em>. List of special entities that appear in the caption, which can be specified instead of <em>parse_mode</em></td>
</tr>
<tr>
<td>show_caption_above_media</td>
<td>Boolean</td>
<td><em>Optional</em>. Pass <em>True</em>, if the caption must be shown above the message media</td>
</tr>
<tr>
<td>video_width</td>
<td>Integer</td>
<td><em>Optional</em>. Video width</td>
</tr>
<tr>
<td>video_height</td>
<td>Integer</td>
<td><em>Optional</em>. Video height</td>
</tr>
<tr>
<td>video_duration</td>
<td>Integer</td>
<td><em>Optional</em>. Video duration in seconds</td>
</tr>
<tr>
<td>description</td>
<td>String</td>
<td><em>Optional</em>. Short description of the result</td>
</tr>
<tr>
<td>reply_markup</td>
<td><a href="#inlinekeyboardmarkup">InlineKeyboardMarkup</a></td>
<td><em>Optional</em>. <a href="/bots/features#inline-keyboards">Inline keyboard</a> attached to the message</td>
</tr>
<tr>
<td>input_message_content</td>
<td><a href="#inputmessagecontent">InputMessageContent</a></td>
<td><em>Optional</em>. Content of the message to be sent instead of the video. This field is <strong>required</strong> if InlineQueryResultVideo is used to send an HTML-page as a result (e.g., a YouTube video).</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="inlinequeryresultaudio" href="#inlinequeryresultaudio"><i class="anchor-icon"></i></a>InlineQueryResultAudio</h4>
<p>Represents a link to an MP3 audio file. By default, this audio file will be sent by the user. Alternatively, you can use <em>input_message_content</em> to send a message with the specified content instead of the audio.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the result, must be <em>audio</em></td>
</tr>
<tr>
<td>id</td>
<td>String</td>
<td>Unique identifier for this result, 1-64 bytes</td>
</tr>
<tr>
<td>audio_url</td>
<td>String</td>
<td>A valid URL for the audio file</td>
</tr>
<tr>
<td>title</td>
<td>String</td>
<td>Title</td>
</tr>
<tr>
<td>caption</td>
<td>String</td>
<td><em>Optional</em>. Caption, 0-1024 characters after entities parsing</td>
</tr>
<tr>
<td>parse_mode</td>
<td>String</td>
<td><em>Optional</em>. Mode for parsing entities in the audio caption. See <a href="#formatting-options">formatting options</a> for more details.</td>
</tr>
<tr>
<td>caption_entities</td>
<td>Array of <a href="#messageentity">MessageEntity</a></td>
<td><em>Optional</em>. List of special entities that appear in the caption, which can be specified instead of <em>parse_mode</em></td>
</tr>
<tr>
<td>performer</td>
<td>String</td>
<td><em>Optional</em>. Performer</td>
</tr>
<tr>
<td>audio_duration</td>
<td>Integer</td>
<td><em>Optional</em>. Audio duration in seconds</td>
</tr>
<tr>
<td>reply_markup</td>
<td><a href="#inlinekeyboardmarkup">InlineKeyboardMarkup</a></td>
<td><em>Optional</em>. <a href="/bots/features#inline-keyboards">Inline keyboard</a> attached to the message</td>
</tr>
<tr>
<td>input_message_content</td>
<td><a href="#inputmessagecontent">InputMessageContent</a></td>
<td><em>Optional</em>. Content of the message to be sent instead of the audio</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="inlinequeryresultvoice" href="#inlinequeryresultvoice"><i class="anchor-icon"></i></a>InlineQueryResultVoice</h4>
<p>Represents a link to a voice recording in an .OGG container encoded with OPUS. By default, this voice recording will be sent by the user. Alternatively, you can use <em>input_message_content</em> to send a message with the specified content instead of the the voice message.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the result, must be <em>voice</em></td>
</tr>
<tr>
<td>id</td>
<td>String</td>
<td>Unique identifier for this result, 1-64 bytes</td>
</tr>
<tr>
<td>voice_url</td>
<td>String</td>
<td>A valid URL for the voice recording</td>
</tr>
<tr>
<td>title</td>
<td>String</td>
<td>Recording title</td>
</tr>
<tr>
<td>caption</td>
<td>String</td>
<td><em>Optional</em>. Caption, 0-1024 characters after entities parsing</td>
</tr>
<tr>
<td>parse_mode</td>
<td>String</td>
<td><em>Optional</em>. Mode for parsing entities in the voice message caption. See <a href="#formatting-options">formatting options</a> for more details.</td>
</tr>
<tr>
<td>caption_entities</td>
<td>Array of <a href="#messageentity">MessageEntity</a></td>
<td><em>Optional</em>. List of special entities that appear in the caption, which can be specified instead of <em>parse_mode</em></td>
</tr>
<tr>
<td>voice_duration</td>
<td>Integer</td>
<td><em>Optional</em>. Recording duration in seconds</td>
</tr>
<tr>
<td>reply_markup</td>
<td><a href="#inlinekeyboardmarkup">InlineKeyboardMarkup</a></td>
<td><em>Optional</em>. <a href="/bots/features#inline-keyboards">Inline keyboard</a> attached to the message</td>
</tr>
<tr>
<td>input_message_content</td>
<td><a href="#inputmessagecontent">InputMessageContent</a></td>
<td><em>Optional</em>. Content of the message to be sent instead of the voice recording</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="inlinequeryresultdocument" href="#inlinequeryresultdocument"><i class="anchor-icon"></i></a>InlineQueryResultDocument</h4>
<p>Represents a link to a file. By default, this file will be sent by the user with an optional caption. Alternatively, you can use <em>input_message_content</em> to send a message with the specified content instead of the file. Currently, only <strong>.PDF</strong> and <strong>.ZIP</strong> files can be sent using this method.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the result, must be <em>document</em></td>
</tr>
<tr>
<td>id</td>
<td>String</td>
<td>Unique identifier for this result, 1-64 bytes</td>
</tr>
<tr>
<td>title</td>
<td>String</td>
<td>Title for the result</td>
</tr>
<tr>
<td>caption</td>
<td>String</td>
<td><em>Optional</em>. Caption of the document to be sent, 0-1024 characters after entities parsing</td>
</tr>
<tr>
<td>parse_mode</td>
<td>String</td>
<td><em>Optional</em>. Mode for parsing entities in the document caption. See <a href="#formatting-options">formatting options</a> for more details.</td>
</tr>
<tr>
<td>caption_entities</td>
<td>Array of <a href="#messageentity">MessageEntity</a></td>
<td><em>Optional</em>. List of special entities that appear in the caption, which can be specified instead of <em>parse_mode</em></td>
</tr>
<tr>
<td>document_url</td>
<td>String</td>
<td>A valid URL for the file</td>
</tr>
<tr>
<td>mime_type</td>
<td>String</td>
<td>MIME type of the content of the file, either “application/pdf” or “application/zip”</td>
</tr>
<tr>
<td>description</td>
<td>String</td>
<td><em>Optional</em>. Short description of the result</td>
</tr>
<tr>
<td>reply_markup</td>
<td><a href="#inlinekeyboardmarkup">InlineKeyboardMarkup</a></td>
<td><em>Optional</em>. <a href="/bots/features#inline-keyboards">Inline keyboard</a> attached to the message</td>
</tr>
<tr>
<td>input_message_content</td>
<td><a href="#inputmessagecontent">InputMessageContent</a></td>
<td><em>Optional</em>. Content of the message to be sent instead of the file</td>
</tr>
<tr>
<td>thumbnail_url</td>
<td>String</td>
<td><em>Optional</em>. URL of the thumbnail (JPEG only) for the file</td>
</tr>
<tr>
<td>thumbnail_width</td>
<td>Integer</td>
<td><em>Optional</em>. Thumbnail width</td>
</tr>
<tr>
<td>thumbnail_height</td>
<td>Integer</td>
<td><em>Optional</em>. Thumbnail height</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="inlinequeryresultlocation" href="#inlinequeryresultlocation"><i class="anchor-icon"></i></a>InlineQueryResultLocation</h4>
<p>Represents a location on a map. By default, the location will be sent by the user. Alternatively, you can use <em>input_message_content</em> to send a message with the specified content instead of the location.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the result, must be <em>location</em></td>
</tr>
<tr>
<td>id</td>
<td>String</td>
<td>Unique identifier for this result, 1-64 Bytes</td>
</tr>
<tr>
<td>latitude</td>
<td>Float</td>
<td>Location latitude in degrees</td>
</tr>
<tr>
<td>longitude</td>
<td>Float</td>
<td>Location longitude in degrees</td>
</tr>
<tr>
<td>title</td>
<td>String</td>
<td>Location title</td>
</tr>
<tr>
<td>horizontal_accuracy</td>
<td>Float</td>
<td><em>Optional</em>. The radius of uncertainty for the location, measured in meters; 0-1500</td>
</tr>
<tr>
<td>live_period</td>
<td>Integer</td>
<td><em>Optional</em>. Period in seconds during which the location can be updated, must be between 60 and 86400, or 0x7FFFFFFF for live locations that can be edited indefinitely</td>
</tr>
<tr>
<td>heading</td>
<td>Integer</td>
<td><em>Optional</em>. For live locations, a direction in which the user is moving, in degrees. Must be between 1 and 360 if specified.</td>
</tr>
<tr>
<td>proximity_alert_radius</td>
<td>Integer</td>
<td><em>Optional</em>. For live locations, a maximum distance for proximity alerts about approaching another chat member, in meters. Must be between 1 and 100000 if specified.</td>
</tr>
<tr>
<td>reply_markup</td>
<td><a href="#inlinekeyboardmarkup">InlineKeyboardMarkup</a></td>
<td><em>Optional</em>. <a href="/bots/features#inline-keyboards">Inline keyboard</a> attached to the message</td>
</tr>
<tr>
<td>input_message_content</td>
<td><a href="#inputmessagecontent">InputMessageContent</a></td>
<td><em>Optional</em>. Content of the message to be sent instead of the location</td>
</tr>
<tr>
<td>thumbnail_url</td>
<td>String</td>
<td><em>Optional</em>. Url of the thumbnail for the result</td>
</tr>
<tr>
<td>thumbnail_width</td>
<td>Integer</td>
<td><em>Optional</em>. Thumbnail width</td>
</tr>
<tr>
<td>thumbnail_height</td>
<td>Integer</td>
<td><em>Optional</em>. Thumbnail height</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="inlinequeryresultvenue" href="#inlinequeryresultvenue"><i class="anchor-icon"></i></a>InlineQueryResultVenue</h4>
<p>Represents a venue. By default, the venue will be sent by the user. Alternatively, you can use <em>input_message_content</em> to send a message with the specified content instead of the venue.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the result, must be <em>venue</em></td>
</tr>
<tr>
<td>id</td>
<td>String</td>
<td>Unique identifier for this result, 1-64 Bytes</td>
</tr>
<tr>
<td>latitude</td>
<td>Float</td>
<td>Latitude of the venue location in degrees</td>
</tr>
<tr>
<td>longitude</td>
<td>Float</td>
<td>Longitude of the venue location in degrees</td>
</tr>
<tr>
<td>title</td>
<td>String</td>
<td>Title of the venue</td>
</tr>
<tr>
<td>address</td>
<td>String</td>
<td>Address of the venue</td>
</tr>
<tr>
<td>foursquare_id</td>
<td>String</td>
<td><em>Optional</em>. Foursquare identifier of the venue if known</td>
</tr>
<tr>
<td>foursquare_type</td>
<td>String</td>
<td><em>Optional</em>. Foursquare type of the venue, if known. (For example, “arts_entertainment/default”, “arts_entertainment/aquarium” or “food/icecream”.)</td>
</tr>
<tr>
<td>google_place_id</td>
<td>String</td>
<td><em>Optional</em>. Google Places identifier of the venue</td>
</tr>
<tr>
<td>google_place_type</td>
<td>String</td>
<td><em>Optional</em>. Google Places type of the venue. (See <a href="https://developers.google.com/places/web-service/supported_types">supported types</a>.)</td>
</tr>
<tr>
<td>reply_markup</td>
<td><a href="#inlinekeyboardmarkup">InlineKeyboardMarkup</a></td>
<td><em>Optional</em>. <a href="/bots/features#inline-keyboards">Inline keyboard</a> attached to the message</td>
</tr>
<tr>
<td>input_message_content</td>
<td><a href="#inputmessagecontent">InputMessageContent</a></td>
<td><em>Optional</em>. Content of the message to be sent instead of the venue</td>
</tr>
<tr>
<td>thumbnail_url</td>
<td>String</td>
<td><em>Optional</em>. Url of the thumbnail for the result</td>
</tr>
<tr>
<td>thumbnail_width</td>
<td>Integer</td>
<td><em>Optional</em>. Thumbnail width</td>
</tr>
<tr>
<td>thumbnail_height</td>
<td>Integer</td>
<td><em>Optional</em>. Thumbnail height</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="inlinequeryresultcontact" href="#inlinequeryresultcontact"><i class="anchor-icon"></i></a>InlineQueryResultContact</h4>
<p>Represents a contact with a phone number. By default, this contact will be sent by the user. Alternatively, you can use <em>input_message_content</em> to send a message with the specified content instead of the contact.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the result, must be <em>contact</em></td>
</tr>
<tr>
<td>id</td>
<td>String</td>
<td>Unique identifier for this result, 1-64 Bytes</td>
</tr>
<tr>
<td>phone_number</td>
<td>String</td>
<td>Contact&#39;s phone number</td>
</tr>
<tr>
<td>first_name</td>
<td>String</td>
<td>Contact&#39;s first name</td>
</tr>
<tr>
<td>last_name</td>
<td>String</td>
<td><em>Optional</em>. Contact&#39;s last name</td>
</tr>
<tr>
<td>vcard</td>
<td>String</td>
<td><em>Optional</em>. Additional data about the contact in the form of a <a href="https://en.wikipedia.org/wiki/VCard">vCard</a>, 0-2048 bytes</td>
</tr>
<tr>
<td>reply_markup</td>
<td><a href="#inlinekeyboardmarkup">InlineKeyboardMarkup</a></td>
<td><em>Optional</em>. <a href="/bots/features#inline-keyboards">Inline keyboard</a> attached to the message</td>
</tr>
<tr>
<td>input_message_content</td>
<td><a href="#inputmessagecontent">InputMessageContent</a></td>
<td><em>Optional</em>. Content of the message to be sent instead of the contact</td>
</tr>
<tr>
<td>thumbnail_url</td>
<td>String</td>
<td><em>Optional</em>. Url of the thumbnail for the result</td>
</tr>
<tr>
<td>thumbnail_width</td>
<td>Integer</td>
<td><em>Optional</em>. Thumbnail width</td>
</tr>
<tr>
<td>thumbnail_height</td>
<td>Integer</td>
<td><em>Optional</em>. Thumbnail height</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="inlinequeryresultgame" href="#inlinequeryresultgame"><i class="anchor-icon"></i></a>InlineQueryResultGame</h4>
<p>Represents a <a href="#games">Game</a>.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the result, must be <em>game</em></td>
</tr>
<tr>
<td>id</td>
<td>String</td>
<td>Unique identifier for this result, 1-64 bytes</td>
</tr>
<tr>
<td>game_short_name</td>
<td>String</td>
<td>Short name of the game</td>
</tr>
<tr>
<td>reply_markup</td>
<td><a href="#inlinekeyboardmarkup">InlineKeyboardMarkup</a></td>
<td><em>Optional</em>. <a href="/bots/features#inline-keyboards">Inline keyboard</a> attached to the message</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="inlinequeryresultcachedphoto" href="#inlinequeryresultcachedphoto"><i class="anchor-icon"></i></a>InlineQueryResultCachedPhoto</h4>
<p>Represents a link to a photo stored on the Telegram servers. By default, this photo will be sent by the user with an optional caption. Alternatively, you can use <em>input_message_content</em> to send a message with the specified content instead of the photo.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the result, must be <em>photo</em></td>
</tr>
<tr>
<td>id</td>
<td>String</td>
<td>Unique identifier for this result, 1-64 bytes</td>
</tr>
<tr>
<td>photo_file_id</td>
<td>String</td>
<td>A valid file identifier of the photo</td>
</tr>
<tr>
<td>title</td>
<td>String</td>
<td><em>Optional</em>. Title for the result</td>
</tr>
<tr>
<td>description</td>
<td>String</td>
<td><em>Optional</em>. Short description of the result</td>
</tr>
<tr>
<td>caption</td>
<td>String</td>
<td><em>Optional</em>. Caption of the photo to be sent, 0-1024 characters after entities parsing</td>
</tr>
<tr>
<td>parse_mode</td>
<td>String</td>
<td><em>Optional</em>. Mode for parsing entities in the photo caption. See <a href="#formatting-options">formatting options</a> for more details.</td>
</tr>
<tr>
<td>caption_entities</td>
<td>Array of <a href="#messageentity">MessageEntity</a></td>
<td><em>Optional</em>. List of special entities that appear in the caption, which can be specified instead of <em>parse_mode</em></td>
</tr>
<tr>
<td>show_caption_above_media</td>
<td>Boolean</td>
<td><em>Optional</em>. Pass <em>True</em>, if the caption must be shown above the message media</td>
</tr>
<tr>
<td>reply_markup</td>
<td><a href="#inlinekeyboardmarkup">InlineKeyboardMarkup</a></td>
<td><em>Optional</em>. <a href="/bots/features#inline-keyboards">Inline keyboard</a> attached to the message</td>
</tr>
<tr>
<td>input_message_content</td>
<td><a href="#inputmessagecontent">InputMessageContent</a></td>
<td><em>Optional</em>. Content of the message to be sent instead of the photo</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="inlinequeryresultcachedgif" href="#inlinequeryresultcachedgif"><i class="anchor-icon"></i></a>InlineQueryResultCachedGif</h4>
<p>Represents a link to an animated GIF file stored on the Telegram servers. By default, this animated GIF file will be sent by the user with an optional caption. Alternatively, you can use <em>input_message_content</em> to send a message with specified content instead of the animation.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the result, must be <em>gif</em></td>
</tr>
<tr>
<td>id</td>
<td>String</td>
<td>Unique identifier for this result, 1-64 bytes</td>
</tr>
<tr>
<td>gif_file_id</td>
<td>String</td>
<td>A valid file identifier for the GIF file</td>
</tr>
<tr>
<td>title</td>
<td>String</td>
<td><em>Optional</em>. Title for the result</td>
</tr>
<tr>
<td>caption</td>
<td>String</td>
<td><em>Optional</em>. Caption of the GIF file to be sent, 0-1024 characters after entities parsing</td>
</tr>
<tr>
<td>parse_mode</td>
<td>String</td>
<td><em>Optional</em>. Mode for parsing entities in the caption. See <a href="#formatting-options">formatting options</a> for more details.</td>
</tr>
<tr>
<td>caption_entities</td>
<td>Array of <a href="#messageentity">MessageEntity</a></td>
<td><em>Optional</em>. List of special entities that appear in the caption, which can be specified instead of <em>parse_mode</em></td>
</tr>
<tr>
<td>show_caption_above_media</td>
<td>Boolean</td>
<td><em>Optional</em>. Pass <em>True</em>, if the caption must be shown above the message media</td>
</tr>
<tr>
<td>reply_markup</td>
<td><a href="#inlinekeyboardmarkup">InlineKeyboardMarkup</a></td>
<td><em>Optional</em>. <a href="/bots/features#inline-keyboards">Inline keyboard</a> attached to the message</td>
</tr>
<tr>
<td>input_message_content</td>
<td><a href="#inputmessagecontent">InputMessageContent</a></td>
<td><em>Optional</em>. Content of the message to be sent instead of the GIF animation</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="inlinequeryresultcachedmpeg4gif" href="#inlinequeryresultcachedmpeg4gif"><i class="anchor-icon"></i></a>InlineQueryResultCachedMpeg4Gif</h4>
<p>Represents a link to a video animation (H.264/MPEG-4 AVC video without sound) stored on the Telegram servers. By default, this animated MPEG-4 file will be sent by the user with an optional caption. Alternatively, you can use <em>input_message_content</em> to send a message with the specified content instead of the animation.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the result, must be <em>mpeg4_gif</em></td>
</tr>
<tr>
<td>id</td>
<td>String</td>
<td>Unique identifier for this result, 1-64 bytes</td>
</tr>
<tr>
<td>mpeg4_file_id</td>
<td>String</td>
<td>A valid file identifier for the MPEG4 file</td>
</tr>
<tr>
<td>title</td>
<td>String</td>
<td><em>Optional</em>. Title for the result</td>
</tr>
<tr>
<td>caption</td>
<td>String</td>
<td><em>Optional</em>. Caption of the MPEG-4 file to be sent, 0-1024 characters after entities parsing</td>
</tr>
<tr>
<td>parse_mode</td>
<td>String</td>
<td><em>Optional</em>. Mode for parsing entities in the caption. See <a href="#formatting-options">formatting options</a> for more details.</td>
</tr>
<tr>
<td>caption_entities</td>
<td>Array of <a href="#messageentity">MessageEntity</a></td>
<td><em>Optional</em>. List of special entities that appear in the caption, which can be specified instead of <em>parse_mode</em></td>
</tr>
<tr>
<td>show_caption_above_media</td>
<td>Boolean</td>
<td><em>Optional</em>. Pass <em>True</em>, if the caption must be shown above the message media</td>
</tr>
<tr>
<td>reply_markup</td>
<td><a href="#inlinekeyboardmarkup">InlineKeyboardMarkup</a></td>
<td><em>Optional</em>. <a href="/bots/features#inline-keyboards">Inline keyboard</a> attached to the message</td>
</tr>
<tr>
<td>input_message_content</td>
<td><a href="#inputmessagecontent">InputMessageContent</a></td>
<td><em>Optional</em>. Content of the message to be sent instead of the video animation</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="inlinequeryresultcachedsticker" href="#inlinequeryresultcachedsticker"><i class="anchor-icon"></i></a>InlineQueryResultCachedSticker</h4>
<p>Represents a link to a sticker stored on the Telegram servers. By default, this sticker will be sent by the user. Alternatively, you can use <em>input_message_content</em> to send a message with the specified content instead of the sticker.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the result, must be <em>sticker</em></td>
</tr>
<tr>
<td>id</td>
<td>String</td>
<td>Unique identifier for this result, 1-64 bytes</td>
</tr>
<tr>
<td>sticker_file_id</td>
<td>String</td>
<td>A valid file identifier of the sticker</td>
</tr>
<tr>
<td>reply_markup</td>
<td><a href="#inlinekeyboardmarkup">InlineKeyboardMarkup</a></td>
<td><em>Optional</em>. <a href="/bots/features#inline-keyboards">Inline keyboard</a> attached to the message</td>
</tr>
<tr>
<td>input_message_content</td>
<td><a href="#inputmessagecontent">InputMessageContent</a></td>
<td><em>Optional</em>. Content of the message to be sent instead of the sticker</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="inlinequeryresultcacheddocument" href="#inlinequeryresultcacheddocument"><i class="anchor-icon"></i></a>InlineQueryResultCachedDocument</h4>
<p>Represents a link to a file stored on the Telegram servers. By default, this file will be sent by the user with an optional caption. Alternatively, you can use <em>input_message_content</em> to send a message with the specified content instead of the file.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the result, must be <em>document</em></td>
</tr>
<tr>
<td>id</td>
<td>String</td>
<td>Unique identifier for this result, 1-64 bytes</td>
</tr>
<tr>
<td>title</td>
<td>String</td>
<td>Title for the result</td>
</tr>
<tr>
<td>document_file_id</td>
<td>String</td>
<td>A valid file identifier for the file</td>
</tr>
<tr>
<td>description</td>
<td>String</td>
<td><em>Optional</em>. Short description of the result</td>
</tr>
<tr>
<td>caption</td>
<td>String</td>
<td><em>Optional</em>. Caption of the document to be sent, 0-1024 characters after entities parsing</td>
</tr>
<tr>
<td>parse_mode</td>
<td>String</td>
<td><em>Optional</em>. Mode for parsing entities in the document caption. See <a href="#formatting-options">formatting options</a> for more details.</td>
</tr>
<tr>
<td>caption_entities</td>
<td>Array of <a href="#messageentity">MessageEntity</a></td>
<td><em>Optional</em>. List of special entities that appear in the caption, which can be specified instead of <em>parse_mode</em></td>
</tr>
<tr>
<td>reply_markup</td>
<td><a href="#inlinekeyboardmarkup">InlineKeyboardMarkup</a></td>
<td><em>Optional</em>. <a href="/bots/features#inline-keyboards">Inline keyboard</a> attached to the message</td>
</tr>
<tr>
<td>input_message_content</td>
<td><a href="#inputmessagecontent">InputMessageContent</a></td>
<td><em>Optional</em>. Content of the message to be sent instead of the file</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="inlinequeryresultcachedvideo" href="#inlinequeryresultcachedvideo"><i class="anchor-icon"></i></a>InlineQueryResultCachedVideo</h4>
<p>Represents a link to a video file stored on the Telegram servers. By default, this video file will be sent by the user with an optional caption. Alternatively, you can use <em>input_message_content</em> to send a message with the specified content instead of the video.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the result, must be <em>video</em></td>
</tr>
<tr>
<td>id</td>
<td>String</td>
<td>Unique identifier for this result, 1-64 bytes</td>
</tr>
<tr>
<td>video_file_id</td>
<td>String</td>
<td>A valid file identifier for the video file</td>
</tr>
<tr>
<td>title</td>
<td>String</td>
<td>Title for the result</td>
</tr>
<tr>
<td>description</td>
<td>String</td>
<td><em>Optional</em>. Short description of the result</td>
</tr>
<tr>
<td>caption</td>
<td>String</td>
<td><em>Optional</em>. Caption of the video to be sent, 0-1024 characters after entities parsing</td>
</tr>
<tr>
<td>parse_mode</td>
<td>String</td>
<td><em>Optional</em>. Mode for parsing entities in the video caption. See <a href="#formatting-options">formatting options</a> for more details.</td>
</tr>
<tr>
<td>caption_entities</td>
<td>Array of <a href="#messageentity">MessageEntity</a></td>
<td><em>Optional</em>. List of special entities that appear in the caption, which can be specified instead of <em>parse_mode</em></td>
</tr>
<tr>
<td>show_caption_above_media</td>
<td>Boolean</td>
<td><em>Optional</em>. Pass <em>True</em>, if the caption must be shown above the message media</td>
</tr>
<tr>
<td>reply_markup</td>
<td><a href="#inlinekeyboardmarkup">InlineKeyboardMarkup</a></td>
<td><em>Optional</em>. <a href="/bots/features#inline-keyboards">Inline keyboard</a> attached to the message</td>
</tr>
<tr>
<td>input_message_content</td>
<td><a href="#inputmessagecontent">InputMessageContent</a></td>
<td><em>Optional</em>. Content of the message to be sent instead of the video</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="inlinequeryresultcachedvoice" href="#inlinequeryresultcachedvoice"><i class="anchor-icon"></i></a>InlineQueryResultCachedVoice</h4>
<p>Represents a link to a voice message stored on the Telegram servers. By default, this voice message will be sent by the user. Alternatively, you can use <em>input_message_content</em> to send a message with the specified content instead of the voice message.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the result, must be <em>voice</em></td>
</tr>
<tr>
<td>id</td>
<td>String</td>
<td>Unique identifier for this result, 1-64 bytes</td>
</tr>
<tr>
<td>voice_file_id</td>
<td>String</td>
<td>A valid file identifier for the voice message</td>
</tr>
<tr>
<td>title</td>
<td>String</td>
<td>Voice message title</td>
</tr>
<tr>
<td>caption</td>
<td>String</td>
<td><em>Optional</em>. Caption, 0-1024 characters after entities parsing</td>
</tr>
<tr>
<td>parse_mode</td>
<td>String</td>
<td><em>Optional</em>. Mode for parsing entities in the voice message caption. See <a href="#formatting-options">formatting options</a> for more details.</td>
</tr>
<tr>
<td>caption_entities</td>
<td>Array of <a href="#messageentity">MessageEntity</a></td>
<td><em>Optional</em>. List of special entities that appear in the caption, which can be specified instead of <em>parse_mode</em></td>
</tr>
<tr>
<td>reply_markup</td>
<td><a href="#inlinekeyboardmarkup">InlineKeyboardMarkup</a></td>
<td><em>Optional</em>. <a href="/bots/features#inline-keyboards">Inline keyboard</a> attached to the message</td>
</tr>
<tr>
<td>input_message_content</td>
<td><a href="#inputmessagecontent">InputMessageContent</a></td>
<td><em>Optional</em>. Content of the message to be sent instead of the voice message</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="inlinequeryresultcachedaudio" href="#inlinequeryresultcachedaudio"><i class="anchor-icon"></i></a>InlineQueryResultCachedAudio</h4>
<p>Represents a link to an MP3 audio file stored on the Telegram servers. By default, this audio file will be sent by the user. Alternatively, you can use <em>input_message_content</em> to send a message with the specified content instead of the audio.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the result, must be <em>audio</em></td>
</tr>
<tr>
<td>id</td>
<td>String</td>
<td>Unique identifier for this result, 1-64 bytes</td>
</tr>
<tr>
<td>audio_file_id</td>
<td>String</td>
<td>A valid file identifier for the audio file</td>
</tr>
<tr>
<td>caption</td>
<td>String</td>
<td><em>Optional</em>. Caption, 0-1024 characters after entities parsing</td>
</tr>
<tr>
<td>parse_mode</td>
<td>String</td>
<td><em>Optional</em>. Mode for parsing entities in the audio caption. See <a href="#formatting-options">formatting options</a> for more details.</td>
</tr>
<tr>
<td>caption_entities</td>
<td>Array of <a href="#messageentity">MessageEntity</a></td>
<td><em>Optional</em>. List of special entities that appear in the caption, which can be specified instead of <em>parse_mode</em></td>
</tr>
<tr>
<td>reply_markup</td>
<td><a href="#inlinekeyboardmarkup">InlineKeyboardMarkup</a></td>
<td><em>Optional</em>. <a href="/bots/features#inline-keyboards">Inline keyboard</a> attached to the message</td>
</tr>
<tr>
<td>input_message_content</td>
<td><a href="#inputmessagecontent">InputMessageContent</a></td>
<td><em>Optional</em>. Content of the message to be sent instead of the audio</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="inputmessagecontent" href="#inputmessagecontent"><i class="anchor-icon"></i></a>InputMessageContent</h4>
<p>This object represents the content of a message to be sent as a result of an inline query. Telegram clients currently support the following types:</p>
<ul>
<li><a href="#inputtextmessagecontent">InputTextMessageContent</a></li>
<li><a href="#inputrichmessagecontent">InputRichMessageContent</a></li>
<li><a href="#inputlocationmessagecontent">InputLocationMessageContent</a></li>
<li><a href="#inputvenuemessagecontent">InputVenueMessageContent</a></li>
<li><a href="#inputcontactmessagecontent">InputContactMessageContent</a></li>
<li><a href="#inputinvoicemessagecontent">InputInvoiceMessageContent</a></li>
</ul>
<h4><a class="anchor" name="inputtextmessagecontent" href="#inputtextmessagecontent"><i class="anchor-icon"></i></a>InputTextMessageContent</h4>
<p>Represents the <a href="#inputmessagecontent">content</a> of a text message to be sent as the result of an inline query.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>message_text</td>
<td>String</td>
<td>Text of the message to be sent, 1-4096 characters</td>
</tr>
<tr>
<td>parse_mode</td>
<td>String</td>
<td><em>Optional</em>. Mode for parsing entities in the message text. See <a href="#formatting-options">formatting options</a> for more details.</td>
</tr>
<tr>
<td>entities</td>
<td>Array of <a href="#messageentity">MessageEntity</a></td>
<td><em>Optional</em>. List of special entities that appear in message text, which can be specified instead of <em>parse_mode</em></td>
</tr>
<tr>
<td>link_preview_options</td>
<td><a href="#linkpreviewoptions">LinkPreviewOptions</a></td>
<td><em>Optional</em>. Link preview generation options for the message</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="inputrichmessagecontent" href="#inputrichmessagecontent"><i class="anchor-icon"></i></a>InputRichMessageContent</h4>
<p>Represents the <a href="#inputmessagecontent">content</a> of a rich message to be sent as the result of an inline query.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>rich_message</td>
<td><a href="#inputrichmessage">InputRichMessage</a></td>
<td>The message to be sent</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="inputlocationmessagecontent" href="#inputlocationmessagecontent"><i class="anchor-icon"></i></a>InputLocationMessageContent</h4>
<p>Represents the <a href="#inputmessagecontent">content</a> of a location message to be sent as the result of an inline query.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>latitude</td>
<td>Float</td>
<td>Latitude of the location in degrees</td>
</tr>
<tr>
<td>longitude</td>
<td>Float</td>
<td>Longitude of the location in degrees</td>
</tr>
<tr>
<td>horizontal_accuracy</td>
<td>Float</td>
<td><em>Optional</em>. The radius of uncertainty for the location, measured in meters; 0-1500</td>
</tr>
<tr>
<td>live_period</td>
<td>Integer</td>
<td><em>Optional</em>. Period in seconds during which the location can be updated, must be between 60 and 86400, or 0x7FFFFFFF for live locations that can be edited indefinitely</td>
</tr>
<tr>
<td>heading</td>
<td>Integer</td>
<td><em>Optional</em>. For live locations, a direction in which the user is moving, in degrees. Must be between 1 and 360 if specified.</td>
</tr>
<tr>
<td>proximity_alert_radius</td>
<td>Integer</td>
<td><em>Optional</em>. For live locations, a maximum distance for proximity alerts about approaching another chat member, in meters. Must be between 1 and 100000 if specified.</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="inputvenuemessagecontent" href="#inputvenuemessagecontent"><i class="anchor-icon"></i></a>InputVenueMessageContent</h4>
<p>Represents the <a href="#inputmessagecontent">content</a> of a venue message to be sent as the result of an inline query.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>latitude</td>
<td>Float</td>
<td>Latitude of the venue in degrees</td>
</tr>
<tr>
<td>longitude</td>
<td>Float</td>
<td>Longitude of the venue in degrees</td>
</tr>
<tr>
<td>title</td>
<td>String</td>
<td>Name of the venue</td>
</tr>
<tr>
<td>address</td>
<td>String</td>
<td>Address of the venue</td>
</tr>
<tr>
<td>foursquare_id</td>
<td>String</td>
<td><em>Optional</em>. Foursquare identifier of the venue, if known</td>
</tr>
<tr>
<td>foursquare_type</td>
<td>String</td>
<td><em>Optional</em>. Foursquare type of the venue, if known. (For example, “arts_entertainment/default”, “arts_entertainment/aquarium” or “food/icecream”.)</td>
</tr>
<tr>
<td>google_place_id</td>
<td>String</td>
<td><em>Optional</em>. Google Places identifier of the venue</td>
</tr>
<tr>
<td>google_place_type</td>
<td>String</td>
<td><em>Optional</em>. Google Places type of the venue. (See <a href="https://developers.google.com/places/web-service/supported_types">supported types</a>.)</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="inputcontactmessagecontent" href="#inputcontactmessagecontent"><i class="anchor-icon"></i></a>InputContactMessageContent</h4>
<p>Represents the <a href="#inputmessagecontent">content</a> of a contact message to be sent as the result of an inline query.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>phone_number</td>
<td>String</td>
<td>Contact&#39;s phone number</td>
</tr>
<tr>
<td>first_name</td>
<td>String</td>
<td>Contact&#39;s first name</td>
</tr>
<tr>
<td>last_name</td>
<td>String</td>
<td><em>Optional</em>. Contact&#39;s last name</td>
</tr>
<tr>
<td>vcard</td>
<td>String</td>
<td><em>Optional</em>. Additional data about the contact in the form of a <a href="https://en.wikipedia.org/wiki/VCard">vCard</a>, 0-2048 bytes</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="inputinvoicemessagecontent" href="#inputinvoicemessagecontent"><i class="anchor-icon"></i></a>InputInvoiceMessageContent</h4>
<p>Represents the <a href="#inputmessagecontent">content</a> of an invoice message to be sent as the result of an inline query.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>title</td>
<td>String</td>
<td>Product name, 1-32 characters</td>
</tr>
<tr>
<td>description</td>
<td>String</td>
<td>Product description, 1-255 characters</td>
</tr>
<tr>
<td>payload</td>
<td>String</td>
<td>Bot-defined invoice payload, 1-128 bytes. This will not be displayed to the user, use it for your internal processes.</td>
</tr>
<tr>
<td>provider_token</td>
<td>String</td>
<td><em>Optional</em>. Payment provider token, obtained via <a href="https://t.me/botfather">@BotFather</a>. Pass an empty string for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>currency</td>
<td>String</td>
<td>Three-letter ISO 4217 currency code, see <a href="/bots/payments#supported-currencies">more on currencies</a>. Pass “XTR” for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>prices</td>
<td>Array of <a href="#labeledprice">LabeledPrice</a></td>
<td>Price breakdown, a JSON-serialized list of components (e.g. product price, tax, discount, delivery cost, delivery tax, bonus, etc.). Must contain exactly one item for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>max_tip_amount</td>
<td>Integer</td>
<td><em>Optional</em>. The maximum accepted amount for tips in the <em>smallest units</em> of the currency (integer, <strong>not</strong> float/double). For example, for a maximum tip of <code>US$ 1.45</code> pass <code>max_tip_amount = 145</code>. See the <em>exp</em> parameter in <a href="/bots/payments/currencies.json">currencies.json</a>, it shows the number of digits past the decimal point for each currency (2 for the majority of currencies). Defaults to 0. Not supported for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>suggested_tip_amounts</td>
<td>Array of Integer</td>
<td><em>Optional</em>. A JSON-serialized array of suggested amounts of tip in the <em>smallest units</em> of the currency (integer, <strong>not</strong> float/double). At most 4 suggested tip amounts can be specified. The suggested tip amounts must be positive, passed in a strictly increased order and must not exceed <em>max_tip_amount</em>.</td>
</tr>
<tr>
<td>provider_data</td>
<td>String</td>
<td><em>Optional</em>. A JSON-serialized object for data about the invoice, which will be shared with the payment provider. A detailed description of the required fields should be provided by the payment provider.</td>
</tr>
<tr>
<td>photo_url</td>
<td>String</td>
<td><em>Optional</em>. URL of the product photo for the invoice. Can be a photo of the goods or a marketing image for a service.</td>
</tr>
<tr>
<td>photo_size</td>
<td>Integer</td>
<td><em>Optional</em>. Photo size in bytes</td>
</tr>
<tr>
<td>photo_width</td>
<td>Integer</td>
<td><em>Optional</em>. Photo width</td>
</tr>
<tr>
<td>photo_height</td>
<td>Integer</td>
<td><em>Optional</em>. Photo height</td>
</tr>
<tr>
<td>need_name</td>
<td>Boolean</td>
<td><em>Optional</em>. Pass <em>True</em> if you require the user&#39;s full name to complete the order. Ignored for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>need_phone_number</td>
<td>Boolean</td>
<td><em>Optional</em>. Pass <em>True</em> if you require the user&#39;s phone number to complete the order. Ignored for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>need_email</td>
<td>Boolean</td>
<td><em>Optional</em>. Pass <em>True</em> if you require the user&#39;s email address to complete the order. Ignored for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>need_shipping_address</td>
<td>Boolean</td>
<td><em>Optional</em>. Pass <em>True</em> if you require the user&#39;s shipping address to complete the order. Ignored for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>send_phone_number_to_provider</td>
<td>Boolean</td>
<td><em>Optional</em>. Pass <em>True</em> if the user&#39;s phone number should be sent to the provider. Ignored for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>send_email_to_provider</td>
<td>Boolean</td>
<td><em>Optional</em>. Pass <em>True</em> if the user&#39;s email address should be sent to the provider. Ignored for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>is_flexible</td>
<td>Boolean</td>
<td><em>Optional</em>. Pass <em>True</em> if the final price depends on the shipping method. Ignored for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="choseninlineresult" href="#choseninlineresult"><i class="anchor-icon"></i></a>ChosenInlineResult</h4>
<p>Represents a <a href="#inlinequeryresult">result</a> of an inline query that was chosen by the user and sent to their chat partner.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>result_id</td>
<td>String</td>
<td>The unique identifier for the result that was chosen</td>
</tr>
<tr>
<td>from</td>
<td><a href="#user">User</a></td>
<td>The user that chose the result</td>
</tr>
<tr>
<td>location</td>
<td><a href="#location">Location</a></td>
<td><em>Optional</em>. Sender location, only for bots that require user location</td>
</tr>
<tr>
<td>inline_message_id</td>
<td>String</td>
<td><em>Optional</em>. Identifier of the sent inline message. Available only if there is an <a href="#inlinekeyboardmarkup">inline keyboard</a> attached to the message. Will be also received in <a href="#callbackquery">callback queries</a> and can be used to <a href="#updating-messages">edit</a> the message.</td>
</tr>
<tr>
<td>query</td>
<td>String</td>
<td>The query that was used to obtain the result</td>
</tr>
</tbody>
</table>
<p><strong>Note:</strong> It is necessary to enable <a href="/bots/inline#collecting-feedback">inline feedback</a> via <a href="https://t.me/botfather">@BotFather</a> in order to receive these objects in updates.</p>
<h3><a class="anchor" name="payments" href="#payments"><i class="anchor-icon"></i></a>Payments</h3>
<p>Your bot can accept payments from Telegram users. Please see the <a href="/bots/payments">introduction to payments</a> for more details on the process and how to set up payments for your bot.</p>
<h4><a class="anchor" name="sendinvoice" href="#sendinvoice"><i class="anchor-icon"></i></a>sendInvoice</h4>
<p>Use this method to send invoices. On success, the sent <a href="#message">Message</a> is returned.</p>
<table class="table">
<thead>
<tr>
<th>Parameter</th>
<th>Type</th>
<th>Required</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>chat_id</td>
<td>Integer or String</td>
<td>Yes</td>
<td>Unique identifier for the target chat or username of the target bot, supergroup or channel in the format <code>@username</code></td>
</tr>
<tr>
<td>message_thread_id</td>
<td>Integer</td>
<td>Optional</td>
<td>Unique identifier for the target message thread (topic) of a forum; for forum supergroups and private chats of bots with forum topic mode enabled only</td>
</tr>
<tr>
<td>direct_messages_topic_id</td>
<td>Integer</td>
<td>Optional</td>
<td>Identifier of the direct messages topic to which the message will be sent; required if the message is sent to a direct messages chat</td>
</tr>
<tr>
<td>title</td>
<td>String</td>
<td>Yes</td>
<td>Product name, 1-32 characters</td>
</tr>
<tr>
<td>description</td>
<td>String</td>
<td>Yes</td>
<td>Product description, 1-255 characters</td>
</tr>
<tr>
<td>payload</td>
<td>String</td>
<td>Yes</td>
<td>Bot-defined invoice payload, 1-128 bytes. This will not be displayed to the user, use it for your internal processes.</td>
</tr>
<tr>
<td>provider_token</td>
<td>String</td>
<td>Optional</td>
<td>Payment provider token, obtained via <a href="https://t.me/botfather">@BotFather</a>. Pass an empty string for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>currency</td>
<td>String</td>
<td>Yes</td>
<td>Three-letter ISO 4217 currency code, see <a href="/bots/payments#supported-currencies">more on currencies</a>. Pass “XTR” for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>prices</td>
<td>Array of <a href="#labeledprice">LabeledPrice</a></td>
<td>Yes</td>
<td>Price breakdown, a JSON-serialized list of components (e.g. product price, tax, discount, delivery cost, delivery tax, bonus, etc.). Must contain exactly one item for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>max_tip_amount</td>
<td>Integer</td>
<td>Optional</td>
<td>The maximum accepted amount for tips in the <em>smallest units</em> of the currency (integer, <strong>not</strong> float/double). For example, for a maximum tip of <code>US$ 1.45</code> pass <code>max_tip_amount = 145</code>. See the <em>exp</em> parameter in <a href="/bots/payments/currencies.json">currencies.json</a>, it shows the number of digits past the decimal point for each currency (2 for the majority of currencies). Defaults to 0. Not supported for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>suggested_tip_amounts</td>
<td>Array of Integer</td>
<td>Optional</td>
<td>A JSON-serialized array of suggested amounts of tips in the <em>smallest units</em> of the currency (integer, <strong>not</strong> float/double). At most 4 suggested tip amounts can be specified. The suggested tip amounts must be positive, passed in a strictly increased order and must not exceed <em>max_tip_amount</em>.</td>
</tr>
<tr>
<td>start_parameter</td>
<td>String</td>
<td>Optional</td>
<td>Unique deep-linking parameter. If left empty, <strong>forwarded copies</strong> of the sent message will have a <em>Pay</em> button, allowing multiple users to pay directly from the forwarded message, using the same invoice. If non-empty, forwarded copies of the sent message will have a <em>URL</em> button with a deep link to the bot (instead of a <em>Pay</em> button), with the value used as the start parameter.</td>
</tr>
<tr>
<td>provider_data</td>
<td>String</td>
<td>Optional</td>
<td>JSON-serialized data about the invoice, which will be shared with the payment provider. A detailed description of required fields should be provided by the payment provider.</td>
</tr>
<tr>
<td>photo_url</td>
<td>String</td>
<td>Optional</td>
<td>URL of the product photo for the invoice. Can be a photo of the goods or a marketing image for a service. People like it better when they see what they are paying for.</td>
</tr>
<tr>
<td>photo_size</td>
<td>Integer</td>
<td>Optional</td>
<td>Photo size in bytes</td>
</tr>
<tr>
<td>photo_width</td>
<td>Integer</td>
<td>Optional</td>
<td>Photo width</td>
</tr>
<tr>
<td>photo_height</td>
<td>Integer</td>
<td>Optional</td>
<td>Photo height</td>
</tr>
<tr>
<td>need_name</td>
<td>Boolean</td>
<td>Optional</td>
<td>Pass <em>True</em> if you require the user&#39;s full name to complete the order. Ignored for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>need_phone_number</td>
<td>Boolean</td>
<td>Optional</td>
<td>Pass <em>True</em> if you require the user&#39;s phone number to complete the order. Ignored for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>need_email</td>
<td>Boolean</td>
<td>Optional</td>
<td>Pass <em>True</em> if you require the user&#39;s email address to complete the order. Ignored for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>need_shipping_address</td>
<td>Boolean</td>
<td>Optional</td>
<td>Pass <em>True</em> if you require the user&#39;s shipping address to complete the order. Ignored for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>send_phone_number_to_provider</td>
<td>Boolean</td>
<td>Optional</td>
<td>Pass <em>True</em> if the user&#39;s phone number should be sent to the provider. Ignored for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>send_email_to_provider</td>
<td>Boolean</td>
<td>Optional</td>
<td>Pass <em>True</em> if the user&#39;s email address should be sent to the provider. Ignored for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>is_flexible</td>
<td>Boolean</td>
<td>Optional</td>
<td>Pass <em>True</em> if the final price depends on the shipping method. Ignored for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>disable_notification</td>
<td>Boolean</td>
<td>Optional</td>
<td>Sends the message <a href="https://telegram.org/blog/channels-2-0#silent-messages">silently</a>. Users will receive a notification with no sound.</td>
</tr>
<tr>
<td>protect_content</td>
<td>Boolean</td>
<td>Optional</td>
<td>Protects the contents of the sent message from forwarding and saving</td>
</tr>
<tr>
<td>allow_paid_broadcast</td>
<td>Boolean</td>
<td>Optional</td>
<td>Pass <em>True</em> to allow up to 1000 messages per second, ignoring <a href="https://core.telegram.org/bots/faq#how-can-i-message-all-of-my-bot-39s-subscribers-at-once">broadcasting limits</a> for a fee of 0.1 Telegram Stars per message. The relevant Stars will be withdrawn from the bot&#39;s balance.</td>
</tr>
<tr>
<td>message_effect_id</td>
<td>String</td>
<td>Optional</td>
<td>Unique identifier of the message effect to be added to the message; for private chats only</td>
</tr>
<tr>
<td>suggested_post_parameters</td>
<td><a href="#suggestedpostparameters">SuggestedPostParameters</a></td>
<td>Optional</td>
<td>A JSON-serialized object containing the parameters of the suggested post to send; for direct messages chats only. If the message is sent as a reply to another suggested post, then that suggested post is automatically declined.</td>
</tr>
<tr>
<td>reply_parameters</td>
<td><a href="#replyparameters">ReplyParameters</a></td>
<td>Optional</td>
<td>Description of the message to reply to</td>
</tr>
<tr>
<td>reply_markup</td>
<td><a href="#inlinekeyboardmarkup">InlineKeyboardMarkup</a></td>
<td>Optional</td>
<td>A JSON-serialized object for an <a href="/bots/features#inline-keyboards">inline keyboard</a>. If empty, one &#39;Pay <code>total price</code>&#39; button will be shown. If not empty, the first button must be a Pay button.</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="createinvoicelink" href="#createinvoicelink"><i class="anchor-icon"></i></a>createInvoiceLink</h4>
<p>Use this method to create a link for an invoice. Returns the created invoice link as <em>String</em> on success.</p>
<table class="table">
<thead>
<tr>
<th>Parameter</th>
<th>Type</th>
<th>Required</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>business_connection_id</td>
<td>String</td>
<td>Optional</td>
<td>Unique identifier of the business connection on behalf of which the link will be created. For payments in <a href="https://t.me/BotNews/90">Telegram Stars</a> only.</td>
</tr>
<tr>
<td>title</td>
<td>String</td>
<td>Yes</td>
<td>Product name, 1-32 characters</td>
</tr>
<tr>
<td>description</td>
<td>String</td>
<td>Yes</td>
<td>Product description, 1-255 characters</td>
</tr>
<tr>
<td>payload</td>
<td>String</td>
<td>Yes</td>
<td>Bot-defined invoice payload, 1-128 bytes. This will not be displayed to the user, use it for your internal processes.</td>
</tr>
<tr>
<td>provider_token</td>
<td>String</td>
<td>Optional</td>
<td>Payment provider token, obtained via <a href="https://t.me/botfather">@BotFather</a>. Pass an empty string for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>currency</td>
<td>String</td>
<td>Yes</td>
<td>Three-letter ISO 4217 currency code, see <a href="/bots/payments#supported-currencies">more on currencies</a>. Pass “XTR” for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>prices</td>
<td>Array of <a href="#labeledprice">LabeledPrice</a></td>
<td>Yes</td>
<td>Price breakdown, a JSON-serialized list of components (e.g. product price, tax, discount, delivery cost, delivery tax, bonus, etc.). Must contain exactly one item for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>subscription_period</td>
<td>Integer</td>
<td>Optional</td>
<td>The number of seconds the subscription will be active for before the next payment. The currency must be set to “XTR” (Telegram Stars) if the parameter is used. Currently, it must always be 2592000 (30 days) if specified. Any number of subscriptions can be active for a given bot at the same time, including multiple concurrent subscriptions from the same user. Subscription price must no exceed 10000 Telegram Stars.</td>
</tr>
<tr>
<td>max_tip_amount</td>
<td>Integer</td>
<td>Optional</td>
<td>The maximum accepted amount for tips in the <em>smallest units</em> of the currency (integer, <strong>not</strong> float/double). For example, for a maximum tip of <code>US$ 1.45</code> pass <code>max_tip_amount = 145</code>. See the <em>exp</em> parameter in <a href="/bots/payments/currencies.json">currencies.json</a>, it shows the number of digits past the decimal point for each currency (2 for the majority of currencies). Defaults to 0. Not supported for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>suggested_tip_amounts</td>
<td>Array of Integer</td>
<td>Optional</td>
<td>A JSON-serialized array of suggested amounts of tips in the <em>smallest units</em> of the currency (integer, <strong>not</strong> float/double). At most 4 suggested tip amounts can be specified. The suggested tip amounts must be positive, passed in a strictly increased order and must not exceed <em>max_tip_amount</em>.</td>
</tr>
<tr>
<td>provider_data</td>
<td>String</td>
<td>Optional</td>
<td>JSON-serialized data about the invoice, which will be shared with the payment provider. A detailed description of required fields should be provided by the payment provider.</td>
</tr>
<tr>
<td>photo_url</td>
<td>String</td>
<td>Optional</td>
<td>URL of the product photo for the invoice. Can be a photo of the goods or a marketing image for a service.</td>
</tr>
<tr>
<td>photo_size</td>
<td>Integer</td>
<td>Optional</td>
<td>Photo size in bytes</td>
</tr>
<tr>
<td>photo_width</td>
<td>Integer</td>
<td>Optional</td>
<td>Photo width</td>
</tr>
<tr>
<td>photo_height</td>
<td>Integer</td>
<td>Optional</td>
<td>Photo height</td>
</tr>
<tr>
<td>need_name</td>
<td>Boolean</td>
<td>Optional</td>
<td>Pass <em>True</em> if you require the user&#39;s full name to complete the order. Ignored for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>need_phone_number</td>
<td>Boolean</td>
<td>Optional</td>
<td>Pass <em>True</em> if you require the user&#39;s phone number to complete the order. Ignored for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>need_email</td>
<td>Boolean</td>
<td>Optional</td>
<td>Pass <em>True</em> if you require the user&#39;s email address to complete the order. Ignored for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>need_shipping_address</td>
<td>Boolean</td>
<td>Optional</td>
<td>Pass <em>True</em> if you require the user&#39;s shipping address to complete the order. Ignored for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>send_phone_number_to_provider</td>
<td>Boolean</td>
<td>Optional</td>
<td>Pass <em>True</em> if the user&#39;s phone number should be sent to the provider. Ignored for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>send_email_to_provider</td>
<td>Boolean</td>
<td>Optional</td>
<td>Pass <em>True</em> if the user&#39;s email address should be sent to the provider. Ignored for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
<tr>
<td>is_flexible</td>
<td>Boolean</td>
<td>Optional</td>
<td>Pass <em>True</em> if the final price depends on the shipping method. Ignored for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>.</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="answershippingquery" href="#answershippingquery"><i class="anchor-icon"></i></a>answerShippingQuery</h4>
<p>If you sent an invoice requesting a shipping address and the parameter <em>is_flexible</em> was specified, the Bot API will send an <a href="#update">Update</a> with a <em>shipping_query</em> field to the bot. Use this method to reply to shipping queries. On success, <em>True</em> is returned.</p>
<table class="table">
<thead>
<tr>
<th>Parameter</th>
<th>Type</th>
<th>Required</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>shipping_query_id</td>
<td>String</td>
<td>Yes</td>
<td>Unique identifier for the query to be answered</td>
</tr>
<tr>
<td>ok</td>
<td>Boolean</td>
<td>Yes</td>
<td>Pass <em>True</em> if delivery to the specified address is possible and <em>False</em> if there are any problems (for example, if delivery to the specified address is not possible)</td>
</tr>
<tr>
<td>shipping_options</td>
<td>Array of <a href="#shippingoption">ShippingOption</a></td>
<td>Optional</td>
<td>Required if <em>ok</em> is <em>True</em>. A JSON-serialized array of available shipping options.</td>
</tr>
<tr>
<td>error_message</td>
<td>String</td>
<td>Optional</td>
<td>Required if <em>ok</em> is <em>False</em>. Error message in human readable form that explains why it is impossible to complete the order (e.g. “Sorry, delivery to your desired address is unavailable”). Telegram will display this message to the user.</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="answerprecheckoutquery" href="#answerprecheckoutquery"><i class="anchor-icon"></i></a>answerPreCheckoutQuery</h4>
<p>Once the user has confirmed their payment and shipping details, the Bot API sends the final confirmation in the form of an <a href="#update">Update</a> with the field <em>pre_checkout_query</em>. Use this method to respond to such pre-checkout queries. On success, <em>True</em> is returned. <strong>Note:</strong> The Bot API must receive an answer within 10 seconds after the pre-checkout query was sent.</p>
<table class="table">
<thead>
<tr>
<th>Parameter</th>
<th>Type</th>
<th>Required</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>pre_checkout_query_id</td>
<td>String</td>
<td>Yes</td>
<td>Unique identifier for the query to be answered</td>
</tr>
<tr>
<td>ok</td>
<td>Boolean</td>
<td>Yes</td>
<td>Specify <em>True</em> if everything is alright (goods are available, etc.) and the bot is ready to proceed with the order. Use <em>False</em> if there are any problems.</td>
</tr>
<tr>
<td>error_message</td>
<td>String</td>
<td>Optional</td>
<td>Required if <em>ok</em> is <em>False</em>. Error message in human readable form that explains the reason for failure to proceed with the checkout (e.g. &quot;Sorry, somebody just bought the last of our amazing black T-shirts while you were busy filling out your payment details. Please choose a different color or garment!&quot;). Telegram will display this message to the user.</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="getmystarbalance" href="#getmystarbalance"><i class="anchor-icon"></i></a>getMyStarBalance</h4>
<p>A method to get the current Telegram Stars balance of the bot. Requires no parameters. On success, returns a <a href="#staramount">StarAmount</a> object.</p>
<h4><a class="anchor" name="getstartransactions" href="#getstartransactions"><i class="anchor-icon"></i></a>getStarTransactions</h4>
<p>Returns the bot&#39;s Telegram Star transactions in chronological order. On success, returns a <a href="#startransactions">StarTransactions</a> object.</p>
<table class="table">
<thead>
<tr>
<th>Parameter</th>
<th>Type</th>
<th>Required</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>offset</td>
<td>Integer</td>
<td>Optional</td>
<td>Number of transactions to skip in the response</td>
</tr>
<tr>
<td>limit</td>
<td>Integer</td>
<td>Optional</td>
<td>The maximum number of transactions to be retrieved. Values between 1-100 are accepted. Defaults to 100.</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="refundstarpayment" href="#refundstarpayment"><i class="anchor-icon"></i></a>refundStarPayment</h4>
<p>Refunds a successful payment in <a href="https://t.me/BotNews/90">Telegram Stars</a>. Returns <em>True</em> on success.</p>
<table class="table">
<thead>
<tr>
<th>Parameter</th>
<th>Type</th>
<th>Required</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>user_id</td>
<td>Integer</td>
<td>Yes</td>
<td>Identifier of the user whose payment will be refunded</td>
</tr>
<tr>
<td>telegram_payment_charge_id</td>
<td>String</td>
<td>Yes</td>
<td>Telegram payment identifier</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="edituserstarsubscription" href="#edituserstarsubscription"><i class="anchor-icon"></i></a>editUserStarSubscription</h4>
<p>Allows the bot to cancel or re-enable extension of a subscription paid in Telegram Stars. Returns <em>True</em> on success.</p>
<table class="table">
<thead>
<tr>
<th>Parameter</th>
<th>Type</th>
<th>Required</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>user_id</td>
<td>Integer</td>
<td>Yes</td>
<td>Identifier of the user whose subscription will be edited</td>
</tr>
<tr>
<td>telegram_payment_charge_id</td>
<td>String</td>
<td>Yes</td>
<td>Telegram payment identifier for the subscription</td>
</tr>
<tr>
<td>is_canceled</td>
<td>Boolean</td>
<td>Yes</td>
<td>Pass <em>True</em> to cancel extension of the user subscription; the subscription must be active up to the end of the current subscription period. Pass <em>False</em> to allow the user to re-enable a subscription that was previously canceled by the bot.</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="labeledprice" href="#labeledprice"><i class="anchor-icon"></i></a>LabeledPrice</h4>
<p>This object represents a portion of the price for goods or services.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>label</td>
<td>String</td>
<td>Portion label</td>
</tr>
<tr>
<td>amount</td>
<td>Integer</td>
<td>Price of the product in the <em>smallest units</em> of the <a href="/bots/payments#supported-currencies">currency</a> (integer, <strong>not</strong> float/double). For example, for a price of <code>US$ 1.45</code> pass <code>amount = 145</code>. See the <em>exp</em> parameter in <a href="/bots/payments/currencies.json">currencies.json</a>, it shows the number of digits past the decimal point for each currency (2 for the majority of currencies).</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="invoice" href="#invoice"><i class="anchor-icon"></i></a>Invoice</h4>
<p>This object contains basic information about an invoice.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>title</td>
<td>String</td>
<td>Product name</td>
</tr>
<tr>
<td>description</td>
<td>String</td>
<td>Product description</td>
</tr>
<tr>
<td>start_parameter</td>
<td>String</td>
<td>Unique bot deep-linking parameter that can be used to generate this invoice</td>
</tr>
<tr>
<td>currency</td>
<td>String</td>
<td>Three-letter ISO 4217 <a href="/bots/payments#supported-currencies">currency</a> code, or “XTR” for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a></td>
</tr>
<tr>
<td>total_amount</td>
<td>Integer</td>
<td>Total price in the <em>smallest units</em> of the currency (integer, <strong>not</strong> float/double). For example, for a price of <code>US$ 1.45</code> pass <code>amount = 145</code>. See the <em>exp</em> parameter in <a href="/bots/payments/currencies.json">currencies.json</a>, it shows the number of digits past the decimal point for each currency (2 for the majority of currencies).</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="shippingaddress" href="#shippingaddress"><i class="anchor-icon"></i></a>ShippingAddress</h4>
<p>This object represents a shipping address.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>country_code</td>
<td>String</td>
<td>Two-letter <a href="https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2">ISO 3166-1 alpha-2</a> country code</td>
</tr>
<tr>
<td>state</td>
<td>String</td>
<td>State, if applicable</td>
</tr>
<tr>
<td>city</td>
<td>String</td>
<td>City</td>
</tr>
<tr>
<td>street_line1</td>
<td>String</td>
<td>First line for the address</td>
</tr>
<tr>
<td>street_line2</td>
<td>String</td>
<td>Second line for the address</td>
</tr>
<tr>
<td>post_code</td>
<td>String</td>
<td>Address post code</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="orderinfo" href="#orderinfo"><i class="anchor-icon"></i></a>OrderInfo</h4>
<p>This object represents information about an order.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>name</td>
<td>String</td>
<td><em>Optional</em>. User name</td>
</tr>
<tr>
<td>phone_number</td>
<td>String</td>
<td><em>Optional</em>. User&#39;s phone number</td>
</tr>
<tr>
<td>email</td>
<td>String</td>
<td><em>Optional</em>. User email</td>
</tr>
<tr>
<td>shipping_address</td>
<td><a href="#shippingaddress">ShippingAddress</a></td>
<td><em>Optional</em>. User shipping address</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="shippingoption" href="#shippingoption"><i class="anchor-icon"></i></a>ShippingOption</h4>
<p>This object represents one shipping option.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>id</td>
<td>String</td>
<td>Shipping option identifier</td>
</tr>
<tr>
<td>title</td>
<td>String</td>
<td>Option title</td>
</tr>
<tr>
<td>prices</td>
<td>Array of <a href="#labeledprice">LabeledPrice</a></td>
<td>List of price portions</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="successfulpayment" href="#successfulpayment"><i class="anchor-icon"></i></a>SuccessfulPayment</h4>
<p>This object contains basic information about a successful payment. Note that if the buyer initiates a chargeback with the relevant payment provider following this transaction, the funds may be debited from your balance. This is outside of Telegram&#39;s control.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>currency</td>
<td>String</td>
<td>Three-letter ISO 4217 <a href="/bots/payments#supported-currencies">currency</a> code, or “XTR” for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a></td>
</tr>
<tr>
<td>total_amount</td>
<td>Integer</td>
<td>Total price in the <em>smallest units</em> of the currency (integer, <strong>not</strong> float/double). For example, for a price of <code>US$ 1.45</code> pass <code>amount = 145</code>. See the <em>exp</em> parameter in <a href="/bots/payments/currencies.json">currencies.json</a>, it shows the number of digits past the decimal point for each currency (2 for the majority of currencies).</td>
</tr>
<tr>
<td>invoice_payload</td>
<td>String</td>
<td>Bot-specified invoice payload</td>
</tr>
<tr>
<td>subscription_expiration_date</td>
<td>Integer</td>
<td><em>Optional</em>. Expiration date of the subscription, in Unix time; for recurring payments only</td>
</tr>
<tr>
<td>is_recurring</td>
<td>True</td>
<td><em>Optional</em>. <em>True</em>, if the payment is a recurring payment for a subscription</td>
</tr>
<tr>
<td>is_first_recurring</td>
<td>True</td>
<td><em>Optional</em>. <em>True</em>, if the payment is the first payment for a subscription</td>
</tr>
<tr>
<td>shipping_option_id</td>
<td>String</td>
<td><em>Optional</em>. Identifier of the shipping option chosen by the user</td>
</tr>
<tr>
<td>order_info</td>
<td><a href="#orderinfo">OrderInfo</a></td>
<td><em>Optional</em>. Order information provided by the user</td>
</tr>
<tr>
<td>telegram_payment_charge_id</td>
<td>String</td>
<td>Telegram payment identifier</td>
</tr>
<tr>
<td>provider_payment_charge_id</td>
<td>String</td>
<td>Provider payment identifier</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="refundedpayment" href="#refundedpayment"><i class="anchor-icon"></i></a>RefundedPayment</h4>
<p>This object contains basic information about a refunded payment.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>currency</td>
<td>String</td>
<td>Three-letter ISO 4217 <a href="/bots/payments#supported-currencies">currency</a> code, or “XTR” for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a>. Currently, always “XTR”.</td>
</tr>
<tr>
<td>total_amount</td>
<td>Integer</td>
<td>Total refunded price in the <em>smallest units</em> of the currency (integer, <strong>not</strong> float/double). For example, for a price of <code>US$ 1.45</code>, <code>total_amount = 145</code>. See the <em>exp</em> parameter in <a href="/bots/payments/currencies.json">currencies.json</a>, it shows the number of digits past the decimal point for each currency (2 for the majority of currencies).</td>
</tr>
<tr>
<td>invoice_payload</td>
<td>String</td>
<td>Bot-specified invoice payload</td>
</tr>
<tr>
<td>telegram_payment_charge_id</td>
<td>String</td>
<td>Telegram payment identifier</td>
</tr>
<tr>
<td>provider_payment_charge_id</td>
<td>String</td>
<td><em>Optional</em>. Provider payment identifier</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="shippingquery" href="#shippingquery"><i class="anchor-icon"></i></a>ShippingQuery</h4>
<p>This object contains information about an incoming shipping query.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>id</td>
<td>String</td>
<td>Unique query identifier</td>
</tr>
<tr>
<td>from</td>
<td><a href="#user">User</a></td>
<td>User who sent the query</td>
</tr>
<tr>
<td>invoice_payload</td>
<td>String</td>
<td>Bot-specified invoice payload</td>
</tr>
<tr>
<td>shipping_address</td>
<td><a href="#shippingaddress">ShippingAddress</a></td>
<td>User specified shipping address</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="precheckoutquery" href="#precheckoutquery"><i class="anchor-icon"></i></a>PreCheckoutQuery</h4>
<p>This object contains information about an incoming pre-checkout query.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>id</td>
<td>String</td>
<td>Unique query identifier</td>
</tr>
<tr>
<td>from</td>
<td><a href="#user">User</a></td>
<td>User who sent the query</td>
</tr>
<tr>
<td>currency</td>
<td>String</td>
<td>Three-letter ISO 4217 <a href="/bots/payments#supported-currencies">currency</a> code, or “XTR” for payments in <a href="https://t.me/BotNews/90">Telegram Stars</a></td>
</tr>
<tr>
<td>total_amount</td>
<td>Integer</td>
<td>Total price in the <em>smallest units</em> of the currency (integer, <strong>not</strong> float/double). For example, for a price of <code>US$ 1.45</code> pass <code>amount = 145</code>. See the <em>exp</em> parameter in <a href="/bots/payments/currencies.json">currencies.json</a>, it shows the number of digits past the decimal point for each currency (2 for the majority of currencies).</td>
</tr>
<tr>
<td>invoice_payload</td>
<td>String</td>
<td>Bot-specified invoice payload</td>
</tr>
<tr>
<td>shipping_option_id</td>
<td>String</td>
<td><em>Optional</em>. Identifier of the shipping option chosen by the user</td>
</tr>
<tr>
<td>order_info</td>
<td><a href="#orderinfo">OrderInfo</a></td>
<td><em>Optional</em>. Order information provided by the user</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="paidmediapurchased" href="#paidmediapurchased"><i class="anchor-icon"></i></a>PaidMediaPurchased</h4>
<p>This object contains information about a paid media purchase.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>from</td>
<td><a href="#user">User</a></td>
<td>User who purchased the media</td>
</tr>
<tr>
<td>paid_media_payload</td>
<td>String</td>
<td>Bot-specified paid media payload</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="revenuewithdrawalstate" href="#revenuewithdrawalstate"><i class="anchor-icon"></i></a>RevenueWithdrawalState</h4>
<p>This object describes the state of a revenue withdrawal operation. Currently, it can be one of</p>
<ul>
<li><a href="#revenuewithdrawalstatepending">RevenueWithdrawalStatePending</a></li>
<li><a href="#revenuewithdrawalstatesucceeded">RevenueWithdrawalStateSucceeded</a></li>
<li><a href="#revenuewithdrawalstatefailed">RevenueWithdrawalStateFailed</a></li>
</ul>
<h4><a class="anchor" name="revenuewithdrawalstatepending" href="#revenuewithdrawalstatepending"><i class="anchor-icon"></i></a>RevenueWithdrawalStatePending</h4>
<p>The withdrawal is in progress.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the state, always “pending”</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="revenuewithdrawalstatesucceeded" href="#revenuewithdrawalstatesucceeded"><i class="anchor-icon"></i></a>RevenueWithdrawalStateSucceeded</h4>
<p>The withdrawal succeeded.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the state, always “succeeded”</td>
</tr>
<tr>
<td>date</td>
<td>Integer</td>
<td>Date the withdrawal was completed in Unix time</td>
</tr>
<tr>
<td>url</td>
<td>String</td>
<td>An HTTPS URL that can be used to see transaction details</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="revenuewithdrawalstatefailed" href="#revenuewithdrawalstatefailed"><i class="anchor-icon"></i></a>RevenueWithdrawalStateFailed</h4>
<p>The withdrawal failed and the transaction was refunded.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the state, always “failed”</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="affiliateinfo" href="#affiliateinfo"><i class="anchor-icon"></i></a>AffiliateInfo</h4>
<p>Contains information about the affiliate that received a commission via this transaction.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>affiliate_user</td>
<td><a href="#user">User</a></td>
<td><em>Optional</em>. The bot or the user that received an affiliate commission if it was received by a bot or a user</td>
</tr>
<tr>
<td>affiliate_chat</td>
<td><a href="#chat">Chat</a></td>
<td><em>Optional</em>. The chat that received an affiliate commission if it was received by a chat</td>
</tr>
<tr>
<td>commission_per_mille</td>
<td>Integer</td>
<td>The number of Telegram Stars received by the affiliate for each 1000 Telegram Stars received by the bot from referred users</td>
</tr>
<tr>
<td>amount</td>
<td>Integer</td>
<td>Integer amount of Telegram Stars received by the affiliate from the transaction, rounded to 0; can be negative for refunds</td>
</tr>
<tr>
<td>nanostar_amount</td>
<td>Integer</td>
<td><em>Optional</em>. The number of 1/1000000000 shares of Telegram Stars received by the affiliate; from -999999999 to 999999999; can be negative for refunds</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="transactionpartner" href="#transactionpartner"><i class="anchor-icon"></i></a>TransactionPartner</h4>
<p>This object describes the source of a transaction, or its recipient for outgoing transactions. Currently, it can be one of</p>
<ul>
<li><a href="#transactionpartneruser">TransactionPartnerUser</a></li>
<li><a href="#transactionpartnerchat">TransactionPartnerChat</a></li>
<li><a href="#transactionpartneraffiliateprogram">TransactionPartnerAffiliateProgram</a></li>
<li><a href="#transactionpartnerfragment">TransactionPartnerFragment</a></li>
<li><a href="#transactionpartnertelegramads">TransactionPartnerTelegramAds</a></li>
<li><a href="#transactionpartnertelegramapi">TransactionPartnerTelegramApi</a></li>
<li><a href="#transactionpartnerother">TransactionPartnerOther</a></li>
</ul>
<h4><a class="anchor" name="transactionpartneruser" href="#transactionpartneruser"><i class="anchor-icon"></i></a>TransactionPartnerUser</h4>
<p>Describes a transaction with a user.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the transaction partner, always “user”</td>
</tr>
<tr>
<td>transaction_type</td>
<td>String</td>
<td>Type of the transaction, currently one of “invoice_payment” for payments via invoices, “paid_media_payment” for payments for paid media, “gift_purchase” for gifts sent by the bot, “premium_purchase” for Telegram Premium subscriptions gifted by the bot, “business_account_transfer” for direct transfers from managed business accounts</td>
</tr>
<tr>
<td>user</td>
<td><a href="#user">User</a></td>
<td>Information about the user</td>
</tr>
<tr>
<td>affiliate</td>
<td><a href="#affiliateinfo">AffiliateInfo</a></td>
<td><em>Optional</em>. Information about the affiliate that received a commission via this transaction. Can be available only for “invoice_payment” and “paid_media_payment” transactions.</td>
</tr>
<tr>
<td>invoice_payload</td>
<td>String</td>
<td><em>Optional</em>. Bot-specified invoice payload. Can be available only for “invoice_payment” transactions.</td>
</tr>
<tr>
<td>subscription_period</td>
<td>Integer</td>
<td><em>Optional</em>. The duration of the paid subscription. Can be available only for “invoice_payment” transactions.</td>
</tr>
<tr>
<td>paid_media</td>
<td>Array of <a href="#paidmedia">PaidMedia</a></td>
<td><em>Optional</em>. Information about the paid media bought by the user; for “paid_media_payment” transactions only</td>
</tr>
<tr>
<td>paid_media_payload</td>
<td>String</td>
<td><em>Optional</em>. Bot-specified paid media payload. Can be available only for “paid_media_payment” transactions.</td>
</tr>
<tr>
<td>gift</td>
<td><a href="#gift">Gift</a></td>
<td><em>Optional</em>. The gift sent to the user by the bot; for “gift_purchase” transactions only</td>
</tr>
<tr>
<td>premium_subscription_duration</td>
<td>Integer</td>
<td><em>Optional</em>. Number of months the gifted Telegram Premium subscription will be active for; for “premium_purchase” transactions only</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="transactionpartnerchat" href="#transactionpartnerchat"><i class="anchor-icon"></i></a>TransactionPartnerChat</h4>
<p>Describes a transaction with a chat.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the transaction partner, always “chat”</td>
</tr>
<tr>
<td>chat</td>
<td><a href="#chat">Chat</a></td>
<td>Information about the chat</td>
</tr>
<tr>
<td>gift</td>
<td><a href="#gift">Gift</a></td>
<td><em>Optional</em>. The gift sent to the chat by the bot</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="transactionpartneraffiliateprogram" href="#transactionpartneraffiliateprogram"><i class="anchor-icon"></i></a>TransactionPartnerAffiliateProgram</h4>
<p>Describes the affiliate program that issued the affiliate commission received via this transaction.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the transaction partner, always “affiliate_program”</td>
</tr>
<tr>
<td>sponsor_user</td>
<td><a href="#user">User</a></td>
<td><em>Optional</em>. Information about the bot that sponsored the affiliate program</td>
</tr>
<tr>
<td>commission_per_mille</td>
<td>Integer</td>
<td>The number of Telegram Stars received by the bot for each 1000 Telegram Stars received by the affiliate program sponsor from referred users</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="transactionpartnerfragment" href="#transactionpartnerfragment"><i class="anchor-icon"></i></a>TransactionPartnerFragment</h4>
<p>Describes a withdrawal transaction with Fragment.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the transaction partner, always “fragment”</td>
</tr>
<tr>
<td>withdrawal_state</td>
<td><a href="#revenuewithdrawalstate">RevenueWithdrawalState</a></td>
<td><em>Optional</em>. State of the transaction if the transaction is outgoing</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="transactionpartnertelegramads" href="#transactionpartnertelegramads"><i class="anchor-icon"></i></a>TransactionPartnerTelegramAds</h4>
<p>Describes a withdrawal transaction to the Telegram Ads platform.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the transaction partner, always “telegram_ads”</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="transactionpartnertelegramapi" href="#transactionpartnertelegramapi"><i class="anchor-icon"></i></a>TransactionPartnerTelegramApi</h4>
<p>Describes a transaction with payment for <a href="#paid-broadcasts">paid broadcasting</a>.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the transaction partner, always “telegram_api”</td>
</tr>
<tr>
<td>request_count</td>
<td>Integer</td>
<td>The number of successful requests that exceeded regular limits and were therefore billed</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="transactionpartnerother" href="#transactionpartnerother"><i class="anchor-icon"></i></a>TransactionPartnerOther</h4>
<p>Describes a transaction with an unknown source or recipient.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Type of the transaction partner, always “other”</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="startransaction" href="#startransaction"><i class="anchor-icon"></i></a>StarTransaction</h4>
<p>Describes a Telegram Star transaction. Note that if the buyer initiates a chargeback with the payment provider from whom they acquired Stars (e.g., Apple, Google) following this transaction, the refunded Stars will be deducted from the bot&#39;s balance. This is outside of Telegram&#39;s control.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>id</td>
<td>String</td>
<td>Unique identifier of the transaction. Coincides with the identifier of the original transaction for refund transactions. Coincides with <em>SuccessfulPayment.telegram_payment_charge_id</em> for successful incoming payments from users.</td>
</tr>
<tr>
<td>amount</td>
<td>Integer</td>
<td>Integer amount of Telegram Stars transferred by the transaction</td>
</tr>
<tr>
<td>nanostar_amount</td>
<td>Integer</td>
<td><em>Optional</em>. The number of 1/1000000000 shares of Telegram Stars transferred by the transaction; from 0 to 999999999</td>
</tr>
<tr>
<td>date</td>
<td>Integer</td>
<td>Date the transaction was created in Unix time</td>
</tr>
<tr>
<td>source</td>
<td><a href="#transactionpartner">TransactionPartner</a></td>
<td><em>Optional</em>. Source of an incoming transaction (e.g., a user purchasing goods or services, Fragment refunding a failed withdrawal). Only for incoming transactions.</td>
</tr>
<tr>
<td>receiver</td>
<td><a href="#transactionpartner">TransactionPartner</a></td>
<td><em>Optional</em>. Receiver of an outgoing transaction (e.g., a user for a purchase refund, Fragment for a withdrawal). Only for outgoing transactions.</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="startransactions" href="#startransactions"><i class="anchor-icon"></i></a>StarTransactions</h4>
<p>Contains a list of Telegram Star transactions.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>transactions</td>
<td>Array of <a href="#startransaction">StarTransaction</a></td>
<td>The list of transactions</td>
</tr>
</tbody>
</table>
<h3><a class="anchor" name="telegram-passport" href="#telegram-passport"><i class="anchor-icon"></i></a>Telegram Passport</h3>
<p><strong>Telegram Passport</strong> is a unified authorization method for services that require personal identification. Users can upload their documents once, then instantly share their data with services that require real-world ID (finance, ICOs, etc.). Please see the <a href="/passport">manual</a> for details.</p>
<h4><a class="anchor" name="passportdata" href="#passportdata"><i class="anchor-icon"></i></a>PassportData</h4>
<p>Describes Telegram Passport data shared with the bot by the user.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>data</td>
<td>Array of <a href="#encryptedpassportelement">EncryptedPassportElement</a></td>
<td>Array with information about documents and other Telegram Passport elements that was shared with the bot</td>
</tr>
<tr>
<td>credentials</td>
<td><a href="#encryptedcredentials">EncryptedCredentials</a></td>
<td>Encrypted credentials required to decrypt the data</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="passportfile" href="#passportfile"><i class="anchor-icon"></i></a>PassportFile</h4>
<p>This object represents a file uploaded to Telegram Passport. Currently all Telegram Passport files are in JPEG format when decrypted and don&#39;t exceed 10MB.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>file_id</td>
<td>String</td>
<td>Identifier for this file, which can be used to download or reuse the file</td>
</tr>
<tr>
<td>file_unique_id</td>
<td>String</td>
<td>Unique identifier for this file, which is supposed to be the same over time and for different bots. Can&#39;t be used to download or reuse the file.</td>
</tr>
<tr>
<td>file_size</td>
<td>Integer</td>
<td>File size in bytes</td>
</tr>
<tr>
<td>file_date</td>
<td>Integer</td>
<td>Unix time when the file was uploaded</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="encryptedpassportelement" href="#encryptedpassportelement"><i class="anchor-icon"></i></a>EncryptedPassportElement</h4>
<p>Describes documents or other Telegram Passport elements shared with the bot by the user.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>type</td>
<td>String</td>
<td>Element type. One of “personal_details”, “passport”, “driver_license”, “identity_card”, “internal_passport”, “address”, “utility_bill”, “bank_statement”, “rental_agreement”, “passport_registration”, “temporary_registration”, “phone_number”, “email”.</td>
</tr>
<tr>
<td>data</td>
<td>String</td>
<td><em>Optional</em>. Base64-encoded encrypted Telegram Passport element data provided by the user; available only for “personal_details”, “passport”, “driver_license”, “identity_card”, “internal_passport” and “address” types. Can be decrypted and verified using the accompanying <a href="#encryptedcredentials">EncryptedCredentials</a>.</td>
</tr>
<tr>
<td>phone_number</td>
<td>String</td>
<td><em>Optional</em>. User&#39;s verified phone number; available only for “phone_number” type</td>
</tr>
<tr>
<td>email</td>
<td>String</td>
<td><em>Optional</em>. User&#39;s verified email address; available only for “email” type</td>
</tr>
<tr>
<td>files</td>
<td>Array of <a href="#passportfile">PassportFile</a></td>
<td><em>Optional</em>. Array of encrypted files with documents provided by the user; available only for “utility_bill”, “bank_statement”, “rental_agreement”, “passport_registration” and “temporary_registration” types. Files can be decrypted and verified using the accompanying <a href="#encryptedcredentials">EncryptedCredentials</a>.</td>
</tr>
<tr>
<td>front_side</td>
<td><a href="#passportfile">PassportFile</a></td>
<td><em>Optional</em>. Encrypted file with the front side of the document, provided by the user; available only for “passport”, “driver_license”, “identity_card” and “internal_passport”. The file can be decrypted and verified using the accompanying <a href="#encryptedcredentials">EncryptedCredentials</a>.</td>
</tr>
<tr>
<td>reverse_side</td>
<td><a href="#passportfile">PassportFile</a></td>
<td><em>Optional</em>. Encrypted file with the reverse side of the document, provided by the user; available only for “driver_license” and “identity_card”. The file can be decrypted and verified using the accompanying <a href="#encryptedcredentials">EncryptedCredentials</a>.</td>
</tr>
<tr>
<td>selfie</td>
<td><a href="#passportfile">PassportFile</a></td>
<td><em>Optional</em>. Encrypted file with the selfie of the user holding a document, provided by the user; available if requested for “passport”, “driver_license”, “identity_card” and “internal_passport”. The file can be decrypted and verified using the accompanying <a href="#encryptedcredentials">EncryptedCredentials</a>.</td>
</tr>
<tr>
<td>translation</td>
<td>Array of <a href="#passportfile">PassportFile</a></td>
<td><em>Optional</em>. Array of encrypted files with translated versions of documents provided by the user; available if requested for “passport”, “driver_license”, “identity_card”, “internal_passport”, “utility_bill”, “bank_statement”, “rental_agreement”, “passport_registration” and “temporary_registration” types. Files can be decrypted and verified using the accompanying <a href="#encryptedcredentials">EncryptedCredentials</a>.</td>
</tr>
<tr>
<td>hash</td>
<td>String</td>
<td>Base64-encoded element hash for using in <a href="#passportelementerrorunspecified">PassportElementErrorUnspecified</a></td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="encryptedcredentials" href="#encryptedcredentials"><i class="anchor-icon"></i></a>EncryptedCredentials</h4>
<p>Describes data required for decrypting and authenticating <a href="#encryptedpassportelement">EncryptedPassportElement</a>. See the <a href="/passport#receiving-information">Telegram Passport Documentation</a> for a complete description of the data decryption and authentication processes.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>data</td>
<td>String</td>
<td>Base64-encoded encrypted JSON-serialized data with unique user&#39;s payload, data hashes and secrets required for <a href="#encryptedpassportelement">EncryptedPassportElement</a> decryption and authentication</td>
</tr>
<tr>
<td>hash</td>
<td>String</td>
<td>Base64-encoded data hash for data authentication</td>
</tr>
<tr>
<td>secret</td>
<td>String</td>
<td>Base64-encoded secret, encrypted with the bot&#39;s public RSA key, required for data decryption</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="setpassportdataerrors" href="#setpassportdataerrors"><i class="anchor-icon"></i></a>setPassportDataErrors</h4>
<p>Informs a user that some of the Telegram Passport elements they provided contains errors. The user will not be able to re-submit their Passport to you until the errors are fixed (the contents of the field for which you returned the error must change). Returns <em>True</em> on success.</p>
<p>Use this if the data submitted by the user doesn&#39;t satisfy the standards your service requires for any reason. For example, if a birthday date seems invalid, a submitted document is blurry, a scan shows evidence of tampering, etc. Supply some details in the error message to make sure the user knows how to correct the issues.</p>
<table class="table">
<thead>
<tr>
<th>Parameter</th>
<th>Type</th>
<th>Required</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>user_id</td>
<td>Integer</td>
<td>Yes</td>
<td>User identifier</td>
</tr>
<tr>
<td>errors</td>
<td>Array of <a href="#passportelementerror">PassportElementError</a></td>
<td>Yes</td>
<td>A JSON-serialized array describing the errors</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="passportelementerror" href="#passportelementerror"><i class="anchor-icon"></i></a>PassportElementError</h4>
<p>This object represents an error in the Telegram Passport element which was submitted that should be resolved by the user. It should be one of:</p>
<ul>
<li><a href="#passportelementerrordatafield">PassportElementErrorDataField</a></li>
<li><a href="#passportelementerrorfrontside">PassportElementErrorFrontSide</a></li>
<li><a href="#passportelementerrorreverseside">PassportElementErrorReverseSide</a></li>
<li><a href="#passportelementerrorselfie">PassportElementErrorSelfie</a></li>
<li><a href="#passportelementerrorfile">PassportElementErrorFile</a></li>
<li><a href="#passportelementerrorfiles">PassportElementErrorFiles</a></li>
<li><a href="#passportelementerrortranslationfile">PassportElementErrorTranslationFile</a></li>
<li><a href="#passportelementerrortranslationfiles">PassportElementErrorTranslationFiles</a></li>
<li><a href="#passportelementerrorunspecified">PassportElementErrorUnspecified</a></li>
</ul>
<h4><a class="anchor" name="passportelementerrordatafield" href="#passportelementerrordatafield"><i class="anchor-icon"></i></a>PassportElementErrorDataField</h4>
<p>Represents an issue in one of the data fields that was provided by the user. The error is considered resolved when the field&#39;s value changes.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>source</td>
<td>String</td>
<td>Error source, must be <em>data</em></td>
</tr>
<tr>
<td>type</td>
<td>String</td>
<td>The section of the user&#39;s Telegram Passport which has the error, one of “personal_details”, “passport”, “driver_license”, “identity_card”, “internal_passport”, “address”</td>
</tr>
<tr>
<td>field_name</td>
<td>String</td>
<td>Name of the data field which has the error</td>
</tr>
<tr>
<td>data_hash</td>
<td>String</td>
<td>Base64-encoded data hash</td>
</tr>
<tr>
<td>message</td>
<td>String</td>
<td>Error message</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="passportelementerrorfrontside" href="#passportelementerrorfrontside"><i class="anchor-icon"></i></a>PassportElementErrorFrontSide</h4>
<p>Represents an issue with the front side of a document. The error is considered resolved when the file with the front side of the document changes.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>source</td>
<td>String</td>
<td>Error source, must be <em>front_side</em></td>
</tr>
<tr>
<td>type</td>
<td>String</td>
<td>The section of the user&#39;s Telegram Passport which has the issue, one of “passport”, “driver_license”, “identity_card”, “internal_passport”</td>
</tr>
<tr>
<td>file_hash</td>
<td>String</td>
<td>Base64-encoded hash of the file with the front side of the document</td>
</tr>
<tr>
<td>message</td>
<td>String</td>
<td>Error message</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="passportelementerrorreverseside" href="#passportelementerrorreverseside"><i class="anchor-icon"></i></a>PassportElementErrorReverseSide</h4>
<p>Represents an issue with the reverse side of a document. The error is considered resolved when the file with reverse side of the document changes.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>source</td>
<td>String</td>
<td>Error source, must be <em>reverse_side</em></td>
</tr>
<tr>
<td>type</td>
<td>String</td>
<td>The section of the user&#39;s Telegram Passport which has the issue, one of “driver_license”, “identity_card”</td>
</tr>
<tr>
<td>file_hash</td>
<td>String</td>
<td>Base64-encoded hash of the file with the reverse side of the document</td>
</tr>
<tr>
<td>message</td>
<td>String</td>
<td>Error message</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="passportelementerrorselfie" href="#passportelementerrorselfie"><i class="anchor-icon"></i></a>PassportElementErrorSelfie</h4>
<p>Represents an issue with the selfie with a document. The error is considered resolved when the file with the selfie changes.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>source</td>
<td>String</td>
<td>Error source, must be <em>selfie</em></td>
</tr>
<tr>
<td>type</td>
<td>String</td>
<td>The section of the user&#39;s Telegram Passport which has the issue, one of “passport”, “driver_license”, “identity_card”, “internal_passport”</td>
</tr>
<tr>
<td>file_hash</td>
<td>String</td>
<td>Base64-encoded hash of the file with the selfie</td>
</tr>
<tr>
<td>message</td>
<td>String</td>
<td>Error message</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="passportelementerrorfile" href="#passportelementerrorfile"><i class="anchor-icon"></i></a>PassportElementErrorFile</h4>
<p>Represents an issue with a document scan. The error is considered resolved when the file with the document scan changes.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>source</td>
<td>String</td>
<td>Error source, must be <em>file</em></td>
</tr>
<tr>
<td>type</td>
<td>String</td>
<td>The section of the user&#39;s Telegram Passport which has the issue, one of “utility_bill”, “bank_statement”, “rental_agreement”, “passport_registration”, “temporary_registration”</td>
</tr>
<tr>
<td>file_hash</td>
<td>String</td>
<td>Base64-encoded file hash</td>
</tr>
<tr>
<td>message</td>
<td>String</td>
<td>Error message</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="passportelementerrorfiles" href="#passportelementerrorfiles"><i class="anchor-icon"></i></a>PassportElementErrorFiles</h4>
<p>Represents an issue with a list of scans. The error is considered resolved when the list of files containing the scans changes.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>source</td>
<td>String</td>
<td>Error source, must be <em>files</em></td>
</tr>
<tr>
<td>type</td>
<td>String</td>
<td>The section of the user&#39;s Telegram Passport which has the issue, one of “utility_bill”, “bank_statement”, “rental_agreement”, “passport_registration”, “temporary_registration”</td>
</tr>
<tr>
<td>file_hashes</td>
<td>Array of String</td>
<td>List of base64-encoded file hashes</td>
</tr>
<tr>
<td>message</td>
<td>String</td>
<td>Error message</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="passportelementerrortranslationfile" href="#passportelementerrortranslationfile"><i class="anchor-icon"></i></a>PassportElementErrorTranslationFile</h4>
<p>Represents an issue with one of the files that constitute the translation of a document. The error is considered resolved when the file changes.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>source</td>
<td>String</td>
<td>Error source, must be <em>translation_file</em></td>
</tr>
<tr>
<td>type</td>
<td>String</td>
<td>Type of element of the user&#39;s Telegram Passport which has the issue, one of “passport”, “driver_license”, “identity_card”, “internal_passport”, “utility_bill”, “bank_statement”, “rental_agreement”, “passport_registration”, “temporary_registration”</td>
</tr>
<tr>
<td>file_hash</td>
<td>String</td>
<td>Base64-encoded file hash</td>
</tr>
<tr>
<td>message</td>
<td>String</td>
<td>Error message</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="passportelementerrortranslationfiles" href="#passportelementerrortranslationfiles"><i class="anchor-icon"></i></a>PassportElementErrorTranslationFiles</h4>
<p>Represents an issue with the translated version of a document. The error is considered resolved when a file with the document translation change.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>source</td>
<td>String</td>
<td>Error source, must be <em>translation_files</em></td>
</tr>
<tr>
<td>type</td>
<td>String</td>
<td>Type of element of the user&#39;s Telegram Passport which has the issue, one of “passport”, “driver_license”, “identity_card”, “internal_passport”, “utility_bill”, “bank_statement”, “rental_agreement”, “passport_registration”, “temporary_registration”</td>
</tr>
<tr>
<td>file_hashes</td>
<td>Array of String</td>
<td>List of base64-encoded file hashes</td>
</tr>
<tr>
<td>message</td>
<td>String</td>
<td>Error message</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="passportelementerrorunspecified" href="#passportelementerrorunspecified"><i class="anchor-icon"></i></a>PassportElementErrorUnspecified</h4>
<p>Represents an issue in an unspecified place. The error is considered resolved when new data is added.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>source</td>
<td>String</td>
<td>Error source, must be <em>unspecified</em></td>
</tr>
<tr>
<td>type</td>
<td>String</td>
<td>Type of element of the user&#39;s Telegram Passport which has the issue</td>
</tr>
<tr>
<td>element_hash</td>
<td>String</td>
<td>Base64-encoded element hash</td>
</tr>
<tr>
<td>message</td>
<td>String</td>
<td>Error message</td>
</tr>
</tbody>
</table>
<h3><a class="anchor" name="games" href="#games"><i class="anchor-icon"></i></a>Games</h3>
<p>Your bot can offer users <strong>HTML5 games</strong> to play solo or to compete against each other in groups and one-on-one chats. Create games via <a href="https://t.me/botfather">@BotFather</a> using the <em>/newgame</em> command. Please note that this kind of power requires responsibility: you will need to accept the terms for each game that your bots will be offering.</p>
<ul>
<li>Games are a new type of content on Telegram, represented by the <a href="#game">Game</a> and <a href="#inlinequeryresultgame">InlineQueryResultGame</a> objects.</li>
<li>Once you&#39;ve created a game via <a href="https://t.me/botfather">BotFather</a>, you can send games to chats as regular messages using the <a href="#sendgame">sendGame</a> method, or use <a href="#inline-mode">inline mode</a> with <a href="#inlinequeryresultgame">InlineQueryResultGame</a>.</li>
<li>If you send the game message without any buttons, it will automatically have a &#39;Play <em>GameName</em>&#39; button. When this button is pressed, your bot gets a <a href="#callbackquery">CallbackQuery</a> with the <em>game_short_name</em> of the requested game. You provide the correct URL for this particular user and the app opens the game in the in-app browser.</li>
<li>You can manually add multiple buttons to your game message. Please note that the first button in the first row <strong>must always</strong> launch the game, using the field <em>callback_game</em> in <a href="#inlinekeyboardbutton">InlineKeyboardButton</a>. You can add extra buttons according to taste: e.g., for a description of the rules, or to open the game&#39;s official community.</li>
<li>To make your game more attractive, you can upload a GIF animation that demonstrates the game to the users via <a href="https://t.me/botfather">BotFather</a> (see <a href="https://t.me/gamebot?game=lumberjack">Lumberjack</a> for example).</li>
<li>A game message will also display high scores for the current chat. Use <a href="#setgamescore">setGameScore</a> to post high scores to the chat with the game, add the <em>disable_edit_message</em> parameter to disable automatic update of the message with the current scoreboard.</li>
<li>Use <a href="#getgamehighscores">getGameHighScores</a> to get data for in-game high score tables.</li>
<li>You can also add an extra <a href="/bots/games#sharing-your-game-to-telegram-chats">sharing button</a> for users to share their best score to different chats.</li>
<li>For examples of what can be done using this new stuff, check the <a href="https://t.me/gamebot">@gamebot</a> and <a href="https://t.me/gamee">@gamee</a> bots.</li>
</ul>
<h4><a class="anchor" name="sendgame" href="#sendgame"><i class="anchor-icon"></i></a>sendGame</h4>
<p>Use this method to send a game. On success, the sent <a href="#message">Message</a> is returned.</p>
<table class="table">
<thead>
<tr>
<th>Parameter</th>
<th>Type</th>
<th>Required</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>business_connection_id</td>
<td>String</td>
<td>Optional</td>
<td>Unique identifier of the business connection on behalf of which the message will be sent</td>
</tr>
<tr>
<td>chat_id</td>
<td>Integer or String</td>
<td>Yes</td>
<td>Unique identifier for the target chat or username of the target bot in the format <code>@username</code>. Games can&#39;t be sent to channel direct messages chats and channel chats.</td>
</tr>
<tr>
<td>message_thread_id</td>
<td>Integer</td>
<td>Optional</td>
<td>Unique identifier for the target message thread (topic) of a forum; for forum supergroups and private chats of bots with forum topic mode enabled only</td>
</tr>
<tr>
<td>game_short_name</td>
<td>String</td>
<td>Yes</td>
<td>Short name of the game, serves as the unique identifier for the game. Set up your games via <a href="https://t.me/botfather">@BotFather</a>.</td>
</tr>
<tr>
<td>disable_notification</td>
<td>Boolean</td>
<td>Optional</td>
<td>Sends the message <a href="https://telegram.org/blog/channels-2-0#silent-messages">silently</a>. Users will receive a notification with no sound.</td>
</tr>
<tr>
<td>protect_content</td>
<td>Boolean</td>
<td>Optional</td>
<td>Protects the contents of the sent message from forwarding and saving</td>
</tr>
<tr>
<td>allow_paid_broadcast</td>
<td>Boolean</td>
<td>Optional</td>
<td>Pass <em>True</em> to allow up to 1000 messages per second, ignoring <a href="https://core.telegram.org/bots/faq#how-can-i-message-all-of-my-bot-39s-subscribers-at-once">broadcasting limits</a> for a fee of 0.1 Telegram Stars per message. The relevant Stars will be withdrawn from the bot&#39;s balance.</td>
</tr>
<tr>
<td>message_effect_id</td>
<td>String</td>
<td>Optional</td>
<td>Unique identifier of the message effect to be added to the message; for private chats only</td>
</tr>
<tr>
<td>reply_parameters</td>
<td><a href="#replyparameters">ReplyParameters</a></td>
<td>Optional</td>
<td>Description of the message to reply to</td>
</tr>
<tr>
<td>reply_markup</td>
<td><a href="#inlinekeyboardmarkup">InlineKeyboardMarkup</a></td>
<td>Optional</td>
<td>A JSON-serialized object for an <a href="/bots/features#inline-keyboards">inline keyboard</a>. If empty, one &#39;Play game_title&#39; button will be shown. If not empty, the first button must launch the game.</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="game" href="#game"><i class="anchor-icon"></i></a>Game</h4>
<p>This object represents a game. Use BotFather to create and edit games, their short names will act as unique identifiers.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>title</td>
<td>String</td>
<td>Title of the game</td>
</tr>
<tr>
<td>description</td>
<td>String</td>
<td>Description of the game</td>
</tr>
<tr>
<td>photo</td>
<td>Array of <a href="#photosize">PhotoSize</a></td>
<td>Photo that will be displayed in the game message in chats</td>
</tr>
<tr>
<td>text</td>
<td>String</td>
<td><em>Optional</em>. Brief description of the game or high scores included in the game message. Can be automatically edited to include current high scores for the game when the bot calls <a href="#setgamescore">setGameScore</a>, or manually edited using <a href="#editmessagetext">editMessageText</a>. 0-4096 characters.</td>
</tr>
<tr>
<td>text_entities</td>
<td>Array of <a href="#messageentity">MessageEntity</a></td>
<td><em>Optional</em>. Special entities that appear in <em>text</em>, such as usernames, URLs, bot commands, etc.</td>
</tr>
<tr>
<td>animation</td>
<td><a href="#animation">Animation</a></td>
<td><em>Optional</em>. Animation that will be displayed in the game message in chats. Upload via <a href="https://t.me/botfather">BotFather</a>.</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="callbackgame" href="#callbackgame"><i class="anchor-icon"></i></a>CallbackGame</h4>
<p>A placeholder, currently holds no information. Use <a href="https://t.me/botfather">BotFather</a> to set up your game.</p>
<h4><a class="anchor" name="setgamescore" href="#setgamescore"><i class="anchor-icon"></i></a>setGameScore</h4>
<p>Use this method to set the score of the specified user in a game message. On success, if the message is not an inline message, the <a href="#message">Message</a> is returned, otherwise <em>True</em> is returned. Returns an error, if the new score is not greater than the user&#39;s current score in the chat and <em>force</em> is <em>False</em>.</p>
<table class="table">
<thead>
<tr>
<th>Parameter</th>
<th>Type</th>
<th>Required</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>user_id</td>
<td>Integer</td>
<td>Yes</td>
<td>User identifier</td>
</tr>
<tr>
<td>score</td>
<td>Integer</td>
<td>Yes</td>
<td>New score, must be non-negative</td>
</tr>
<tr>
<td>force</td>
<td>Boolean</td>
<td>Optional</td>
<td>Pass <em>True</em> if the high score is allowed to decrease. This can be useful when fixing mistakes or banning cheaters.</td>
</tr>
<tr>
<td>disable_edit_message</td>
<td>Boolean</td>
<td>Optional</td>
<td>Pass <em>True</em> if the game message should not be automatically edited to include the current scoreboard</td>
</tr>
<tr>
<td>chat_id</td>
<td>Integer</td>
<td>Optional</td>
<td>Required if <em>inline_message_id</em> is not specified. Unique identifier for the target chat.</td>
</tr>
<tr>
<td>message_id</td>
<td>Integer</td>
<td>Optional</td>
<td>Required if <em>inline_message_id</em> is not specified. Identifier of the sent message.</td>
</tr>
<tr>
<td>inline_message_id</td>
<td>String</td>
<td>Optional</td>
<td>Required if <em>chat_id</em> and <em>message_id</em> are not specified. Identifier of the inline message.</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="getgamehighscores" href="#getgamehighscores"><i class="anchor-icon"></i></a>getGameHighScores</h4>
<p>Use this method to get data for high score tables. Will return the score of the specified user and several of their neighbors in a game. Returns an Array of <a href="#gamehighscore">GameHighScore</a> objects.</p>
<blockquote>
<p>This method will currently return scores for the target user, plus two of their closest neighbors on each side. Will also return the top three users if the user and their neighbors are not among them. Please note that this behavior is subject to change.</p>
</blockquote>
<table class="table">
<thead>
<tr>
<th>Parameter</th>
<th>Type</th>
<th>Required</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>user_id</td>
<td>Integer</td>
<td>Yes</td>
<td>Target user id</td>
</tr>
<tr>
<td>chat_id</td>
<td>Integer</td>
<td>Optional</td>
<td>Required if <em>inline_message_id</em> is not specified. Unique identifier for the target chat.</td>
</tr>
<tr>
<td>message_id</td>
<td>Integer</td>
<td>Optional</td>
<td>Required if <em>inline_message_id</em> is not specified. Identifier of the sent message.</td>
</tr>
<tr>
<td>inline_message_id</td>
<td>String</td>
<td>Optional</td>
<td>Required if <em>chat_id</em> and <em>message_id</em> are not specified. Identifier of the inline message.</td>
</tr>
</tbody>
</table>
<h4><a class="anchor" name="gamehighscore" href="#gamehighscore"><i class="anchor-icon"></i></a>GameHighScore</h4>
<p>This object represents one row of the high scores table for a game.</p>
<table class="table">
<thead>
<tr>
<th>Field</th>
<th>Type</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>position</td>
<td>Integer</td>
<td>Position in high score table for the game</td>
</tr>
<tr>
<td>user</td>
<td><a href="#user">User</a></td>
<td>User</td>
</tr>
<tr>
<td>score</td>
<td>Integer</td>
<td>Score</td>
</tr>
</tbody>
</table>
<hr>
<p>And that&#39;s about all we&#39;ve got for now.<br>If you&#39;ve got any questions, please check out our <a href="/bots/faq"><strong>Bot FAQ »</strong></a></p>
</div>
  
</div>
          
        </div>
      </div>
      <div class="footer_wrap">
  <div class="footer_columns_wrap footer_desktop">
    <div class="footer_column footer_column_telegram">
      <h5>Telegram</h5>
      <div class="footer_telegram_description"></div>
      Telegram is a cloud-based mobile and desktop messaging app with a focus on security and speed.
    </div>

    <div class="footer_column">
      <h5><a href="//telegram.org/faq">About</a></h5>
      <ul>
        <li><a href="//telegram.org/faq">FAQ</a></li>
        <li><a href="//telegram.org/privacy">Privacy</a></li>
        <li><a href="//telegram.org/press">Press</a></li>
      </ul>
    </div>
    <div class="footer_column">
      <h5><a href="//telegram.org/apps#mobile-apps">Mobile Apps</a></h5>
      <ul>
        <li><a href="//telegram.org/dl/ios">iPhone/iPad</a></li>
        <li><a href="//telegram.org/android">Android</a></li>
        <li><a href="//telegram.org/dl/web">Mobile Web</a></li>
      </ul>
    </div>
    <div class="footer_column">
      <h5><a href="//telegram.org/apps#desktop-apps">Desktop Apps</a></h5>
      <ul>
        <li><a href="//desktop.telegram.org/">PC/Mac/Linux</a></li>
        <li><a href="//macos.telegram.org/">macOS</a></li>
        <li><a href="//telegram.org/dl/web">Web-browser</a></li>
      </ul>
    </div>
    <div class="footer_column footer_column_platform">
      <h5><a href="/">Platform</a></h5>
      <ul>
        <li><a href="/api">API</a></li>
        <li><a href="//translations.telegram.org/">Translations</a></li>
        <li><a href="//instantview.telegram.org/">Instant View</a></li>
      </ul>
    </div>
  </div>
  <div class="footer_columns_wrap footer_mobile">
    <div class="footer_column">
      <h5><a href="//telegram.org/faq">About</a></h5>
    </div>
    <div class="footer_column">
      <h5><a href="//telegram.org/blog">Blog</a></h5>
    </div>
    <div class="footer_column">
      <h5><a href="//telegram.org/press">Press</a></h5>
    </div>
    <div class="footer_column">
      <h5><a href="//telegram.org/safety">Safety</a></h5>
    </div>
  </div>
</div>
    </div>
    <script src="/js/main.js?47"></script>
    <script src="/js/jquery.min.js?1"></script>
<script src="/js/bootstrap.min.js?1"></script>

    <script>window.initDevPageNav&&initDevPageNav();
backToTopInit("Go up");
removePreloadInit();
</script>
  </body>
</html>
<!-- page generated in 173.88ms -->

