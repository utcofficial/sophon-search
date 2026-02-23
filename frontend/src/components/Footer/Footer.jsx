import styles from './Footer.module.css'

function Footer() {
    return (
        <footer className={styles.footer}>
            <div className={styles.footerContent}>
                <div className={styles.brand}>
                    <span className={styles.builtWith}>Built with</span>
                    <span className={styles.heart}>❤</span>
                    <span className={styles.by}>by</span>
                </div>
                
                <div className={styles.credits}>
                    <a 
                        href="https://unitedtechcommunity.in/" 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className={styles.link}
                    >
                        <span className={styles.org}>United Tech Community</span>
                    </a>
                    
                    <span className={styles.separator}>×</span>
                    
                    <a 
                        href="https://sambhavdwivedi.in/" 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className={styles.link}
                    >
                        <span className={styles.name}>Sambhav Dwivedi</span>
                    </a>
                </div>
                
                <div className={styles.copyright}>
                    © {new Date().getFullYear()} Sophon Search
                </div>
            </div>
            
            
            <div className={styles.gradientLine}></div>
        </footer>
    )
}

export default Footer