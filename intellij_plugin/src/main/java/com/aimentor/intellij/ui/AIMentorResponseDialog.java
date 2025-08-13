package com.aimentor.intellij.ui;

import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.editor.EditorFactory;
import com.intellij.openapi.editor.EditorSettings;
import com.intellij.openapi.editor.ex.EditorEx;
import com.intellij.openapi.fileTypes.FileType;
import com.intellij.openapi.fileTypes.FileTypeManager;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.DialogWrapper;
import com.intellij.ui.components.JBLabel;
import com.intellij.ui.components.JBScrollPane;
import com.intellij.util.ui.FormBuilder;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import javax.swing.*;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;

/**
 * Dialog to display AI Mentor responses with syntax highlighting
 */
public class AIMentorResponseDialog extends DialogWrapper {
    private final String question;
    private final String response;
    private final String codeContext;
    private Editor responseEditor;
    private final Project project;
    
    public AIMentorResponseDialog(@Nullable Project project, 
                                 @NotNull String title, 
                                 @NotNull String question, 
                                 @NotNull String response,
                                 @Nullable String codeContext) {
        super(project);
        this.project = project;
        this.question = question;
        this.response = response;
        this.codeContext = codeContext;
        
        setTitle(title);
        setSize(800, 600);
        setResizable(true);
        init();
    }
    
    @Override
    protected @Nullable JComponent createCenterPanel() {
        JPanel mainPanel = new JPanel(new BorderLayout());
        
        // Question section
        JBLabel questionLabel = new JBLabel("Question:");
        questionLabel.setFont(questionLabel.getFont().deriveFont(Font.BOLD));
        
        JTextArea questionArea = new JTextArea(question);
        questionArea.setEditable(false);
        questionArea.setLineWrap(true);
        questionArea.setWrapStyleWord(true);
        questionArea.setRows(2);
        questionArea.setBackground(UIManager.getColor("Panel.background"));
        
        // Response section with syntax highlighting
        JBLabel responseLabel = new JBLabel("AI Mentor Response:");
        responseLabel.setFont(responseLabel.getFont().deriveFont(Font.BOLD));
        
        // Create editor for response with syntax highlighting
        responseEditor = createResponseEditor();
        
        // Code context section (if available)
        JComponent contextComponent = null;
        if (codeContext != null && !codeContext.trim().isEmpty()) {
            JBLabel contextLabel = new JBLabel("Code Context:");
            contextLabel.setFont(contextLabel.getFont().deriveFont(Font.BOLD));
            
            JTextArea contextArea = new JTextArea(codeContext);
            contextArea.setEditable(false);
            contextArea.setFont(new Font(Font.MONOSPACED, Font.PLAIN, 12));
            contextArea.setRows(Math.min(8, codeContext.split("\n").length));
            contextArea.setBackground(UIManager.getColor("Panel.background"));
            
            contextComponent = FormBuilder.createFormBuilder()
                .addComponent(contextLabel)
                .addComponent(new JBScrollPane(contextArea))
                .getPanel();
        }
        
        // Build layout
        FormBuilder builder = FormBuilder.createFormBuilder()
            .addComponent(questionLabel)
            .addComponent(new JBScrollPane(questionArea))
            .addVerticalGap(15)
            .addComponent(responseLabel)
            .addComponent(responseEditor.getComponent());
        
        if (contextComponent != null) {
            builder.addVerticalGap(15)
                   .addComponent(contextComponent);
        }
        
        return builder.getPanel();
    }
    
    private Editor createResponseEditor() {
        // Try to detect if response contains code
        FileType fileType = FileTypeManager.getInstance().getFileTypeByExtension("md");
        if (response.contains("```") || response.contains("public class") || response.contains("def ") || response.contains("function ")) {
            // Try to detect language
            if (response.contains("public class") || response.contains("import java")) {
                fileType = FileTypeManager.getInstance().getFileTypeByExtension("java");
            } else if (response.contains("def ") || response.contains("import ")) {
                fileType = FileTypeManager.getInstance().getFileTypeByExtension("py");
            } else if (response.contains("function ") || response.contains("const ") || response.contains("let ")) {
                fileType = FileTypeManager.getInstance().getFileTypeByExtension("js");
            }
        }
        
        Editor editor = EditorFactory.getInstance().createEditor(
            EditorFactory.getInstance().createDocument(response),
            project,
            fileType,
            true
        );
        
        EditorSettings settings = editor.getSettings();
        settings.setLineNumbersShown(true);
        settings.setFoldingOutlineShown(false);
        settings.setLineMarkerAreaShown(false);
        settings.setIndentGuidesShown(true);
        settings.setVirtualSpace(false);
        
        if (editor instanceof EditorEx) {
            ((EditorEx) editor).setHorizontalScrollbarVisible(true);
            ((EditorEx) editor).setVerticalScrollbarVisible(true);
        }
        
        return editor;
    }
    
    @Override
    protected Action @NotNull [] createActions() {
        return new Action[]{
            new AbstractAction("Copy Response") {
                @Override
                public void actionPerformed(ActionEvent e) {
                    copyResponseToClipboard();
                }
            },
            getOKAction()
        };
    }
    
    private void copyResponseToClipboard() {
        if (responseEditor != null) {
            responseEditor.getSelectionModel().selectAll();
            responseEditor.getContentComponent().copy();
            responseEditor.getSelectionModel().removeSelection();
        }
    }
    
    @Override
    protected void dispose() {
        if (responseEditor != null) {
            EditorFactory.getInstance().releaseEditor(responseEditor);
        }
        super.dispose();
    }
}
