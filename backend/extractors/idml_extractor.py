"""Extract ordered text nodes from an IDML file (ZIP containing Story XMLs)."""

import re
import zipfile
from dataclasses import dataclass, asdict
from lxml import etree


@dataclass
class IdmlTextNode:
    node_id: str          # e.g. "u78f07_p3"
    story_id: str         # e.g. "u78f07"
    paragraph_index: int  # 0-based within story
    text: str             # Concatenated Content text (cleaned)
    style: str            # ParagraphStyleRange AppliedParagraphStyle
    global_order: int     # Sequential order across all stories

    def to_dict(self) -> dict:
        return asdict(self)


# Processing instructions like <?ACE 8?> are decorative markers
ACE_RE = re.compile(r'<\?ACE\s+\d+\?>')


def split_japanese_sentences(text: str) -> list[str]:
    """Split Japanese text into sentence-level chunks, keeping delimiters."""
    if not text:
        return []

    # Keep punctuation and include it with each sentence
    parts = re.split(r'(?<=[。？！]|\.|\?|!)\s*', text)
    parts = [p.strip() for p in parts if p.strip()]
    return parts


def _extract_paragraphs_from_story(story_elem) -> list[tuple[str, str]]:
    """Extract paragraph texts from a Story element.

    Returns list of (text, style) tuples.
    Splits on <Br/> within ParagraphStyleRange.
    """
    paragraphs: list[tuple[str, str]] = []

    for psr in story_elem:
        tag = psr.tag.split('}')[-1] if '}' in psr.tag else psr.tag
        if tag != 'ParagraphStyleRange':
            continue

        style = psr.get('AppliedParagraphStyle', '')

        current_text_parts: list[str] = []

        for csr in psr:
            csr_tag = csr.tag.split('}')[-1] if '}' in csr.tag else csr.tag

            if csr_tag == 'CharacterStyleRange':
                for child in csr:
                    child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag

                    if child_tag == 'Content':
                        text = child.text or ''
                        # Strip ACE processing instructions
                        text = ACE_RE.sub('', text)
                        if text:
                            current_text_parts.append(text)

                    elif child_tag == 'Br':
                        # Paragraph break - flush current text
                        joined = ''.join(current_text_parts).strip()
                        if joined:
                            paragraphs.append((joined, style))
                        current_text_parts = []

            elif csr_tag == 'Table':
                # Extract text from table cells
                for cell in csr.findall('.//{*}Cell'):
                    cell_texts = []
                    for content in cell.findall('.//{*}Content'):
                        t = content.text or ''
                        t = ACE_RE.sub('', t)
                        if t:
                            cell_texts.append(t)
                    cell_text = ''.join(cell_texts).strip()
                    if cell_text:
                        paragraphs.append((cell_text, style))

        # Remaining text after last Br in this ParagraphStyleRange
        joined = ''.join(current_text_parts).strip()
        if joined:
            paragraphs.append((joined, style))

    return paragraphs


def extract_idml_nodes(idml_path: str, min_text_length: int = 2) -> list[IdmlTextNode]:
    """Extract ordered text nodes from an IDML file.

    Args:
        idml_path: Path to the .idml file (which is a ZIP)
        min_text_length: Skip nodes shorter than this (decorative elements)

    Returns:
        List of IdmlTextNode ordered by document position
    """
    nodes: list[IdmlTextNode] = []
    global_order = 0

    with zipfile.ZipFile(idml_path, 'r') as z:
        # Get story order from designmap.xml
        story_order: list[str] = []
        if 'designmap.xml' in z.namelist():
            dm_xml = z.read('designmap.xml').decode('utf-8')
            match = re.search(r'StoryList="([^"]+)"', dm_xml)
            if match:
                story_order = match.group(1).split()

        # Get available story files
        story_files = {
            name.split('/')[-1].replace('Story_', '').replace('.xml', ''): name
            for name in z.namelist()
            if name.startswith('Stories/Story_')
        }

        # Process stories in designmap order, fallback to sorted filenames
        if story_order:
            ordered_ids = [sid for sid in story_order if sid in story_files]
        else:
            ordered_ids = sorted(story_files.keys())

        for story_id in ordered_ids:
            filename = story_files[story_id]
            xml_bytes = z.read(filename)
            root = etree.fromstring(xml_bytes)

            # Find the Story element (child of idPkg:Story)
            story_elem = None
            for child in root:
                child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                if child_tag == 'Story':
                    story_elem = child
                    break

            if story_elem is None:
                continue

            paragraphs = _extract_paragraphs_from_story(story_elem)

            for para_idx, (text, style) in enumerate(paragraphs):
                sentence_texts = split_japanese_sentences(text)

                for sent_idx, sent_text in enumerate(sentence_texts):
                    if len(sent_text) < min_text_length:
                        continue

                    node = IdmlTextNode(
                        node_id=f"{story_id}_p{para_idx}_s{sent_idx}",
                        story_id=story_id,
                        paragraph_index=para_idx,
                        text=sent_text,
                        style=style,
                        global_order=global_order,
                    )
                    nodes.append(node)
                    global_order += 1

    return nodes

import json
import os
DEBUG_FOLDER = "debug"

def _save_debug_ja_nodes(job_id: str, ja_nodes: list[IdmlTextNode]) -> None:
    """Save Japanese nodes to debug folder as JSON."""
    os.makedirs(DEBUG_FOLDER, exist_ok=True)
    path = os.path.join(DEBUG_FOLDER, f"{job_id}_ja_nodes.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump([node.to_dict() for node in ja_nodes], f, ensure_ascii=False, indent=2)
    print(f"Saved JA nodes to {path}")


if __name__ == '__main__':
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else '../doc/ITC_ARJ25.idml'
    nodes = extract_idml_nodes(path)
    print(f'Total nodes: {len(nodes)}')
    for n in nodes:
        display = n.text[:80] + '...' if len(n.text) > 80 else n.text
        print(f'[{n.global_order:3d}] {n.node_id:20s} {display}')
