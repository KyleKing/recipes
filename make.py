import glob
import logging
import re

logger = logging.getLogger(__name__)
lgr_fn = 'recipes.log'
formatter = logging.Formatter('%(asctime)s %(filename)s:%(lineno)d\t%(message)s')

logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(lgr_fn)
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
logger.addHandler(fh)


class website_builder(object):
    """Create a new index.html file based on raw markdown templates"""

    index_html = 'index.html'
    template_top = 'src/html/tmpl_top.html'
    template_bot = 'src/html/tmpl_bot.html'
    src_dir = 'content/'
    src_imgs = 'src/imgs/'

    def __init__(self):
        """Prepare output directory and files"""
        open(self.index_html, 'w').close()

    def make(self):
        """Read from src directory and generate output for website"""
        top = self.read(self.template_top)
        self.write(top)
        sec_name = False
        for markdown_fn in glob.glob('{}*/*.md'.format(self.src_dir)):
            new_sec_name = re.search('\/([^\/]+)\/[^\/]+\.md', markdown_fn).group(1)
            if new_sec_name != sec_name:
                self.start_section(new_sec_name)
                sec_name = new_sec_name
            self.parse_md(markdown_fn)
        bot = self.read(self.template_bot)
        self.write(bot)

    def read(self, fn, split=False):
        """Return the contents of a file"""
        with open(fn) as fn_:
            contents = fn_.read()
        if split:
            return contents.split('\n')
        else:
            return contents

    def write(self, content, raw_fn=False):
        """Append to the html file"""
        fn = raw_fn if raw_fn else self.index_html
        with open(fn, 'ab') as fn_:
            fn_.write(content)

    def start_section(self, sec_name):
        """Start a linkable section header"""
        self.write('\n<h1 id="{sec_name}">{sec_name}</h1>\n'.format(sec_name=sec_name))

    def parse_md(self, fn):
        """Parse each line of the markdown file"""
        self.track_list_stat("init")
        for line in self.read(fn, split=True):
            line = self.italics(line)
            if re.match('^#', line):
                self.init_recipe(line, fn)
            elif re.match('^-\s', line):
                self.track_list_stat('ul')
                self.append_list_item(line.strip('-').strip())
            elif re.match('^\d[\.\)]?\s', line):
                self.track_list_stat('ol')
                parsed = re.search('^\d[\.\)]?\s(.+)', line).group(1).strip()
                self.append_list_item(parsed)
            elif re.match('^end$', line):
                self.track_list_stat('end')
            elif len(line) > 0:
                self.other(line)
        # Add the closing div's
        self.write('\n</div><!-- /columns (list) --></div><!-- /row (recipe) -->\n')
        return line

    def init_recipe(self, raw_title, full_fn):
        # Solve for variables in markdown layout
        base_name = re.search('[^\/]+\/([^.\/]+)\.md', full_fn).group(1)
        title = re.search('#+([^#|]+)', raw_title).group(1).strip()
        header = raw_title.split("||")
        orig_link = header[1].strip() if len(header) == 2 else False
        # Assemble HTML
        classes = 'class="twelve columns" id="recipe-{}"'.format(title)
        html_lnk = '<a href="{}"><i>(Source)</i></a>'.format(orig_link) if orig_link else ''
        ttle_lnk = '<a href="#recipe-{title}" class="unstyled"># {title}</a>'.format(title=title)
        header = '<div class="row br"><h5 {}>{} {}</h5></div>'.format(classes, ttle_lnk, html_lnk)
        for image_name in glob.glob('{}{}.*'.format(self.src_imgs, base_name)):
            break
        else:
            image_name = ''
        img_html = '<div class="row">\n<img {} src="{}", alt="{}"/>'.format(
            'class="five columns"', image_name, base_name)
        text_start = '<div class="seven columns">'
        self.write('\n{}\n{}\n{}'.format(header, img_html, text_start))

    def track_list_stat(self, match_list_type):
        """Track the status of the last list type written"""
        if match_list_type == 'init':
            self.status = {"ol": False, "ul": False}
        elif match_list_type == 'ul':
            if not self.status["ul"]:
                self.write("<ul>")
            self.status = {"ol": False, "ul": True}
        elif match_list_type == 'ol':
            if not self.status["ol"]:
                self.write("<ol>")
            self.status = {"ol": True, "ul": False}
        elif match_list_type == 'end':
            # Close the list div and reset the tracker
            if self.status["ol"]:
                self.write("</ol>")
            elif self.status["ul"]:
                self.write("</ul>")
            self.status = {"ol": False, "ul": False}

    def append_list_item(self, line):
        self.write('<li>{}</li>'.format(line))

    def other(self, line):
        """Write single line notes/extra information"""
        # logger.debug('Writing paragraph for: {}'.format(line))
        self.write('<p>{}</p>'.format(line))
        pass

    def italics(self, raw_line):
        if '**' in raw_line:
            line_sections = raw_line.split('**')
            # count_ln = len(line_sections)
            init = True if raw_line[1:2] == '**' else False
            line = ''
            for ls_, line_sec in enumerate(line_sections):
                if init:
                    html = '<i>' if ls_ % 2 == 1 else '</i>'
                else:
                    html = ''
                    init = True
                line += html + line_sec
            logger.debug('Italics: {} > `{}`\n'.format(line_sections, line))
        else:
            line = raw_line
        return line


if __name__ == '__main__':
    open(lgr_fn, 'w').close()
    website_builder().make()
