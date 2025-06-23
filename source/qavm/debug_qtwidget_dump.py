from pathlib import Path
import html

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
	QWidget, QLabel, QLineEdit, QTextEdit, QComboBox, QPushButton,
	QListWidget, QTableWidget, QPlainTextEdit
)

class QtHTMLDump:
	def __init__(self, root_widget: QWidget):
		self.root = root_widget

	def _get_widget_content(self, widget: QWidget) -> str:
		"""Returns string representation of widget content, if applicable."""
		if isinstance(widget, QLabel):
			return f"Label: {html.escape(widget.text())}"
		elif isinstance(widget, QLineEdit):
			return f"LineEdit: {html.escape(widget.text())}"
		elif isinstance(widget, QTextEdit):
			return f"TextEdit: {html.escape(widget.toPlainText())}"
		elif isinstance(widget, QPlainTextEdit):
			return f"PlainTextEdit: {html.escape(widget.toPlainText())}"
		elif isinstance(widget, QComboBox):
			items = [widget.itemText(i) for i in range(widget.count())]
			current = widget.currentText()
			return f"ComboBox (current='{html.escape(current)}'): [{', '.join(map(html.escape, items))}]"
		elif isinstance(widget, QPushButton):
			return f"Button: {html.escape(widget.text())}"
		elif isinstance(widget, QListWidget):
			items = [widget.item(i).text() for i in range(widget.count())]
			return f"ListWidget: [{', '.join(map(html.escape, items))}]"
		elif isinstance(widget, QTableWidget):
			rows, cols = widget.rowCount(), widget.columnCount()
			cells = []
			for r in range(rows):
				row_items = []
				for c in range(cols):
					item = widget.item(r, c)
					text = item.text() if item else ""
					row_items.append(html.escape(text))
				cells.append(" | ".join(row_items))
			return f"TableWidget ({rows}x{cols}):<br>" + "<br>".join(cells)
		return ""

	def _dump_widget_tree(self, widget: QWidget, level: int = 0) -> str:
		indent = "  " * level
		rect = widget.geometry()
		obj_name = html.escape(widget.objectName() or "unnamed")
		class_name = widget.__class__.__name__
		visible = widget.isVisible()
		size_policy = widget.sizePolicy()
		layout = widget.layout()
		layout_name = layout.__class__.__name__ if layout else "None"

		visibility_class = "invisible" if not visible else ""
		content = self._get_widget_content(widget)

		html_block = (
			f"{indent}<div class='widget {visibility_class}' "
			f"data-class='{class_name}' "
			f"data-name='{obj_name}' "
			f"data-geometry='x:{rect.x()}, y:{rect.y()}, w:{rect.width()}, h:{rect.height()}'>\n"
			f"{indent}  <div class='header' onclick='toggle(this)'>"
			f"<strong>{class_name}</strong> (<code>{obj_name}</code>) — "
			f"<em>{rect.x()},{rect.y()},{rect.width()},{rect.height()}</em><br>"
			f"Layout: {layout_name}, SizePolicy: H={size_policy.horizontalPolicy().name}, V={size_policy.verticalPolicy().name}"
			f"</div>\n"
		)
		if content:
			html_block += f"{indent}  <div class='content'>{content}</div>\n"

		html_block += f"{indent}  <div class='children'>\n"
		for child in sorted(widget.findChildren(QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly), key=lambda c: c.objectName() or ""):
			html_block += self._dump_widget_tree(child, level + 1)
		html_block += f"{indent}  </div>\n{indent}</div>\n"
		return html_block

	def generate_html(self) -> str:
		html_header = """<!DOCTYPE html>
<html><head><meta charset='utf-8'><title>Qt Layout Snapshot</title>
<style>
	body { font-family: sans-serif; font-size: 13px; background: #f0f0f0; color: #333; }
	.widget { border: 1px dashed #999; padding: 6px; margin: 6px; background: #fff; }
	.header { cursor: pointer; background: #e8e8e8; padding: 4px; }
	.children { margin-left: 20px; display: block; }
	.content { margin-left: 12px; color: #555; background: #fefefe; font-family: monospace; white-space: pre-wrap; }
	.invisible .header { color: #999; background: #f5f5f5; }
	code { background: #eee; padding: 0 4px; }
</style>
<script>
	function toggle(header) {
		const children = header.parentElement.querySelector('.children');
		if (children) children.style.display = children.style.display === 'none' ? 'block' : 'none';
	}
</script></head><body>
<h2>Layout Snapshot</h2>
"""
		html_body = self._dump_widget_tree(self.root)
		return f"{html_header}{html_body}</body></html>"

	def save_to_file(self, path: str | Path = "layout_snapshot.html"):
		path = Path(path)
		html = self.generate_html()
		path.write_text(html, encoding="utf-8")
		print(f"[QtHTMLDump] Snapshot saved to: {path.resolve()}")