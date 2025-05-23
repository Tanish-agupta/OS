import javax.swing.*;
import javax.swing.event.*;
import javax.swing.filechooser.FileSystemView;
import javax.swing.table.*;
import javax.swing.tree.*;
import java.awt.*;
import java.awt.event.*;
import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.List;

public class FileExplorer extends JFrame {
    private JTree fileTree;
    private JTable fileTable;
    private JTextField addressBar;
    private JButton backButton;
    private JButton forwardButton;
    private JButton upButton;
    private JButton refreshButton;
    private JButton homeButton;
    private JButton deleteButton;

    private Stack<File> backHistory = new Stack<>();
    private Stack<File> forwardHistory = new Stack<>();
    private File currentDirectory;

    private FileSystemView fileSystemView;
    private DefaultTreeCellRenderer treeCellRenderer;

    public FileExplorer() {
        super("File Explorer");
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setSize(900, 600);
        fileSystemView = FileSystemView.getFileSystemView();
        createComponents();
        setupLayout();
        setupEventHandlers();
        navigateTo(fileSystemView.getHomeDirectory());
    }

    private void createComponents() {
        backButton = new JButton("←");
        backButton.setToolTipText("Back");
        backButton.setEnabled(false);

        forwardButton = new JButton("→");
        forwardButton.setToolTipText("Forward");
        forwardButton.setEnabled(false);

        upButton = new JButton("↑");
        upButton.setToolTipText("Up one level");

        refreshButton = new JButton("⟳");
        refreshButton.setToolTipText("Refresh");

        homeButton = new JButton("🏠");
        homeButton.setToolTipText("Home");

        deleteButton = new JButton("🗑");
        deleteButton.setToolTipText("Delete");

        addressBar = new JTextField();

        DefaultMutableTreeNode root = new DefaultMutableTreeNode("Root");
        File[] rootFiles = File.listRoots();
        for (File rootFile : rootFiles) {
            DefaultMutableTreeNode node = new DefaultMutableTreeNode(rootFile);
            root.add(node);
            if (rootFile.isDirectory()) {
                node.add(new DefaultMutableTreeNode("Loading..."));
            }
        }

        fileTree = new JTree(root);
        fileTree.setRootVisible(false);
        fileTree.setShowsRootHandles(true);

        treeCellRenderer = new DefaultTreeCellRenderer() {
            @Override
            public Component getTreeCellRendererComponent(JTree tree, Object value, boolean selected, boolean expanded, boolean leaf, int row, boolean hasFocus) {
                super.getTreeCellRendererComponent(tree, value, selected, expanded, leaf, row, hasFocus);
                DefaultMutableTreeNode node = (DefaultMutableTreeNode) value;
                if (node.getUserObject() instanceof File) {
                    File file = (File) node.getUserObject();
                    setIcon(fileSystemView.getSystemIcon(file));
                    setText(fileSystemView.getSystemDisplayName(file));
                }
                return this;
            }
        };
        fileTree.setCellRenderer(treeCellRenderer);

        fileTable = new JTable();
        fileTable.setSelectionMode(ListSelectionModel.MULTIPLE_INTERVAL_SELECTION);
        fileTable.setAutoCreateRowSorter(true);
        fileTable.setShowGrid(false);
        fileTable.setIntercellSpacing(new Dimension(0, 0));
    }

    private void setupLayout() {
        setLayout(new BorderLayout());

        JToolBar toolBar = new JToolBar();
        toolBar.setFloatable(false);
        toolBar.add(backButton);
        toolBar.add(forwardButton);
        toolBar.add(upButton);
        toolBar.add(refreshButton);
        toolBar.add(homeButton);
        toolBar.add(deleteButton);
        toolBar.addSeparator();
        toolBar.add(new JLabel("Address: "));
        toolBar.add(addressBar);

        add(toolBar, BorderLayout.NORTH);

        JSplitPane splitPane = new JSplitPane(JSplitPane.HORIZONTAL_SPLIT);
        splitPane.setDividerLocation(200);
        JScrollPane treeScroll = new JScrollPane(fileTree);
        splitPane.setLeftComponent(treeScroll);
        JScrollPane tableScroll = new JScrollPane(fileTable);
        splitPane.setRightComponent(tableScroll);
        add(splitPane, BorderLayout.CENTER);

        JPanel statusBar = new JPanel(new BorderLayout());
        statusBar.setBorder(BorderFactory.createLoweredBevelBorder());
        JLabel statusLabel = new JLabel(" Ready");
        statusBar.add(statusLabel, BorderLayout.WEST);
        add(statusBar, BorderLayout.SOUTH);
    }

    private void setupEventHandlers() {
        fileTree.addTreeSelectionListener(e -> {
            DefaultMutableTreeNode node = (DefaultMutableTreeNode) fileTree.getLastSelectedPathComponent();
            if (node == null || !(node.getUserObject() instanceof File)) return;
            File file = (File) node.getUserObject();
            if (file.isDirectory()) navigateTo(file);
        });

        fileTree.addTreeExpansionListener(new TreeExpansionListener() {
            @Override
            public void treeExpanded(TreeExpansionEvent event) {
                TreePath path = event.getPath();
                DefaultMutableTreeNode node = (DefaultMutableTreeNode) path.getLastPathComponent();
                if (node.getChildCount() == 1 && ((DefaultMutableTreeNode) node.getFirstChild()).getUserObject().equals("Loading...")) {
                    node.removeAllChildren();
                    File directory = (File) node.getUserObject();
                    File[] files = directory.listFiles();
                    if (files != null) {
                        Arrays.sort(files, (a, b) -> {
                            if (a.isDirectory() && !b.isDirectory()) return -1;
                            if (!a.isDirectory() && b.isDirectory()) return 1;
                            return a.getName().compareToIgnoreCase(b.getName());
                        });
                        for (File file : files) {
                            if (file.isHidden()) continue;
                            DefaultMutableTreeNode childNode = new DefaultMutableTreeNode(file);
                            node.add(childNode);
                            if (file.isDirectory()) childNode.add(new DefaultMutableTreeNode("Loading..."));
                        }
                    }
                    ((DefaultTreeModel) fileTree.getModel()).nodeStructureChanged(node);
                }
            }

            @Override
            public void treeCollapsed(TreeExpansionEvent event) {}
        });

        fileTable.addMouseListener(new MouseAdapter() {
            @Override
            public void mouseClicked(MouseEvent e) {
                if (e.getClickCount() == 2) {
                    int row = fileTable.rowAtPoint(e.getPoint());
                    if (row >= 0) {
                        int modelRow = fileTable.convertRowIndexToModel(row);
                        File file = (File) fileTable.getModel().getValueAt(modelRow, 0);
                        if (file.isDirectory()) {
                            navigateTo(file);
                        } else {
                            try {
                                Desktop.getDesktop().open(file);
                            } catch (IOException ex) {
                                JOptionPane.showMessageDialog(FileExplorer.this, "Error opening file: " + ex.getMessage(), "Error", JOptionPane.ERROR_MESSAGE);
                            }
                        }
                    }
                }
            }
        });

        backButton.addActionListener(e -> {
            if (!backHistory.isEmpty()) {
                forwardHistory.push(currentDirectory);
                forwardButton.setEnabled(true);
                File backFile = backHistory.pop();
                if (backHistory.isEmpty()) backButton.setEnabled(false);
                navigateWithoutHistory(backFile);
            }
        });

        forwardButton.addActionListener(e -> {
            if (!forwardHistory.isEmpty()) {
                backHistory.push(currentDirectory);
                backButton.setEnabled(true);
                File forwardFile = forwardHistory.pop();
                if (forwardHistory.isEmpty()) forwardButton.setEnabled(false);
                navigateWithoutHistory(forwardFile);
            }
        });

        upButton.addActionListener(e -> {
            if (currentDirectory != null && currentDirectory.getParentFile() != null) {
                navigateTo(currentDirectory.getParentFile());
            }
        });

        refreshButton.addActionListener(e -> {
            if (currentDirectory != null) {
                navigateWithoutHistory(currentDirectory);
            }
        });

        homeButton.addActionListener(e -> {
            navigateTo(fileSystemView.getHomeDirectory());
        });

        deleteButton.addActionListener(e -> {
            int[] selectedRows = fileTable.getSelectedRows();
            if (selectedRows.length == 0) return;
            List<File> filesToDelete = new ArrayList<>();
            for (int row : selectedRows) {
                int modelRow = fileTable.convertRowIndexToModel(row);
                File file = (File) fileTable.getModel().getValueAt(modelRow, 0);
                filesToDelete.add(file);
            }
            int response = JOptionPane.showConfirmDialog(this, "Are you sure you want to delete the selected " + (filesToDelete.size() == 1 ? "file" : filesToDelete.size() + " files") + "?", "Confirm Delete", JOptionPane.YES_NO_OPTION, JOptionPane.WARNING_MESSAGE);
            if (response == JOptionPane.YES_OPTION) {
                for (File file : filesToDelete) {
                    try {
                        Files.delete(file.toPath());
                    } catch (IOException ex) {
                        JOptionPane.showMessageDialog(this, "Error deleting " + file.getName() + ": " + ex.getMessage(), "Delete Error", JOptionPane.ERROR_MESSAGE);
                    }
                }
                navigateWithoutHistory(currentDirectory);
            }
        });

        addressBar.addActionListener(e -> {
            String address = addressBar.getText().trim();
            Path path = Paths.get(address);
            File file = path.toFile();
            if (file.exists() && file.isDirectory()) {
                navigateTo(file);
            } else {
                JOptionPane.showMessageDialog(this, "Invalid directory path: " + address, "Error", JOptionPane.ERROR_MESSAGE);
                addressBar.setText(currentDirectory.getAbsolutePath());
            }
        });
    }

    private void navigateTo(File directory) {
        if (directory == null || !directory.isDirectory()) return;
        if (currentDirectory != null) {
            backHistory.push(currentDirectory);
            backButton.setEnabled(true);
        }
        forwardHistory.clear();
        forwardButton.setEnabled(false);
        navigateWithoutHistory(directory);
    }

    private void navigateWithoutHistory(File directory) {
        if (directory == null || !directory.isDirectory()) return;
        currentDirectory = directory;
        addressBar.setText(directory.getAbsolutePath());
        selectDirectoryInTree(directory);
        updateFileTable(directory);
        upButton.setEnabled(directory.getParentFile() != null);
    }

    private void selectDirectoryInTree(File directory) {}

    private void updateFileTable(File directory) {
        DefaultTableModel model = new DefaultTableModel() {
            @Override
            public boolean isCellEditable(int row, int column) {
                return false;
            }

            @Override
            public Class<?> getColumnClass(int column) {
                switch (column) {
                    case 0: return File.class;
                    case 1: return String.class;
                    case 2: return String.class;
                    case 3: return Long.class;
                    case 4: return Date.class;
                    default: return Object.class;
                }
            }
        };

        model.addColumn("File");
        model.addColumn("Name");
        model.addColumn("Type");
        model.addColumn("Size");
        model.addColumn("Last Modified");

        File[] files = directory.listFiles();
        if (files != null) {
            Arrays.sort(files, (a, b) -> {
                if (a.isDirectory() && !b.isDirectory()) return -1;
                if (!a.isDirectory() && b.isDirectory()) return 1;
                return a.getName().compareToIgnoreCase(b.getName());
            });

            for (File file : files) {
                if (file.isHidden()) continue;
                Object[] row = new Object[5];
                row[0] = file;
                row[1] = file.getName();
                row[2] = file.isDirectory() ? "Folder" : getFileExtension(file);
                row[3] = file.isDirectory() ? null : file.length();
                row[4] = new Date(file.lastModified());
                model.addRow(row);
            }
        }

        fileTable.setModel(model);
        fileTable.getColumnModel().getColumn(0).setMinWidth(0);
        fileTable.getColumnModel().getColumn(0).setMaxWidth(0);
        fileTable.getColumnModel().getColumn(0).setWidth(0);

        fileTable.getColumnModel().getColumn(1).setCellRenderer(new DefaultTableCellRenderer() {
            @Override
            public Component getTableCellRendererComponent(JTable table, Object value, boolean isSelected, boolean hasFocus, int row, int column) {
                JLabel label = (JLabel) super.getTableCellRendererComponent(table, value, isSelected, hasFocus, row, column);
                int modelRow = table.convertRowIndexToModel(row);
                File file = (File) table.getModel().getValueAt(modelRow, 0);
                label.setIcon(fileSystemView.getSystemIcon(file));
                return label;
            }
        });

        fileTable.getColumnModel().getColumn(3).setCellRenderer(new DefaultTableCellRenderer() {
            @Override
            public Component getTableCellRendererComponent(JTable table, Object value, boolean isSelected, boolean hasFocus, int row, int column) {
                if (value == null) value = "";
                else {
                    long size = (Long) value;
                    if (size < 1024) value = size + " B";
                    else if (size < 1024 * 1024) value = String.format("%.1f KB", size / 1024.0);
                    else if (size < 1024 * 1024 * 1024) value = String.format("%.1f MB", size / (1024.0 * 1024));
                    else value = String.format("%.1f GB", size / (1024.0 * 1024 * 1024));
                }
                JLabel label = (JLabel) super.getTableCellRendererComponent(table, value, isSelected, hasFocus, row, column);
                label.setHorizontalAlignment(JLabel.RIGHT);
                return label;
            }
        });

        fileTable.getColumnModel().getColumn(4).setCellRenderer(new DefaultTableCellRenderer() {
            private SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");

            @Override
            public Component getTableCellRendererComponent(JTable table, Object value, boolean isSelected, boolean hasFocus, int row, int column) {
                if (value instanceof Date) {
                    value = dateFormat.format((Date) value);
                }
                return super.getTableCellRendererComponent(table, value, isSelected, hasFocus, row, column);
            }
        });

        fileTable.getColumnModel().getColumn(1).setPreferredWidth(250);
        fileTable.getColumnModel().getColumn(2).setPreferredWidth(100);
        fileTable.getColumnModel().getColumn(3).setPreferredWidth(100);
        fileTable.getColumnModel().getColumn(4).setPreferredWidth(150);
    }

    private String getFileExtension(File file) {
        String name = file.getName();
        int lastDotIndex = name.lastIndexOf('.');
        if (lastDotIndex > 0 && lastDotIndex < name.length() - 1) {
            return name.substring(lastDotIndex + 1).toUpperCase() + " File";
        }
        return "File";
    }

    public static void main(String[] args) {
        try {
            UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
        } catch (Exception e) {
            e.printStackTrace();
        }

        SwingUtilities.invokeLater(() -> {
            FileExplorer explorer = new FileExplorer();
            explorer.setVisible(true);
        });
    }
}
