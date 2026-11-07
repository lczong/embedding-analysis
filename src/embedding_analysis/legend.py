"""Shared legend layout only; experiments retain their own figures and labels."""
import matplotlib.font_manager as fm


def top_legend(ax, cfg, handles=None, labels=None):
    """Fit a left-aligned legend above the axes/title without widening the plot.

    Measure rendered text and candidate column layouts. Long single entries wrap;
    no category is dropped. Freeze completed axes layout before adding the legend
    so constrained layout cannot shrink the data panel to make room for it.
    """
    if handles is None:
        handles, labels=ax.get_legend_handles_labels()
    elif labels is None:
        labels=[handle.get_label() for handle in handles]
    if not handles:return None
    previous=ax.get_legend()
    if previous is not None:previous.remove()
    fig=ax.figure
    fig.canvas.draw()
    renderer=fig.canvas.get_renderer()
    box=ax.get_window_extent(renderer)
    fontsize=cfg['plot'].get('legend',{}).get('fontsize',10)
    prop=fm.FontProperties(size=fontsize)
    points=fig.dpi/72
    # Reserve handle, handle/text gap and a small rounding margin.
    text_width=max(20,box.width-(2+.6+.4)*fontsize*points)
    def width(text):return renderer.get_text_width_height_descent(text,prop,False)[0]
    def wrap(text):
        lines=[]
        for paragraph in str(text).split('\n'):
            line=''
            for word in paragraph.split():
                if line and width(line+' '+word)>text_width:
                    lines.append(line);line=''
                while width(word)>text_width and len(word)>1:
                    count=1
                    while count<len(word) and width(word[:count+1])<=text_width:count+=1
                    if line:lines.append(line);line=''
                    lines.append(word[:count]);word=word[count:]
                line=(line+' '+word).strip()
            lines.append(line)
        return '\n'.join(lines)
    labels=[wrap(label) for label in labels]
    top=box.y1
    if ax.title.get_text():top=max(top,ax.title.get_window_extent(renderer).y1)
    anchor=fig.transFigure.inverted().transform((box.x0,top+8*points))
    if fig.get_layout_engine() is not None:fig.set_layout_engine(None)
    for columns in range(min(len(handles),12),0,-1):
        legend=ax.legend(handles=handles,labels=labels,loc='lower left',
                         bbox_to_anchor=anchor,bbox_transform=fig.transFigure,
                         borderaxespad=0,borderpad=0,ncol=columns,fontsize=fontsize,
                         frameon=False,handlelength=2,handletextpad=.6,
                         columnspacing=1.2,labelspacing=.45,alignment='left')
        if legend.get_window_extent(renderer).width<=box.width+.5 or columns==1:break
        legend.remove()
    for handle in legend.legend_handles:
        if hasattr(handle,'set_alpha'):handle.set_alpha(1)
    return legend
